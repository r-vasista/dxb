import json
import asyncio

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import F

from chat.models import ChatGroup, ChatMessage, ChatGroupMember, MessageReceipt, ChatClear, DeleteMessage
from chat.choices import MessageType
from chat.utils import (
    is_group_member, broadcast_active_chats_update, async_broadcast_active_chats_update, async_broadcast_presence_update
)
from chat.serializers import ChatMessageSerializer, ChatGroupMiniSerializer
from core.services import get_user_profile
from profiles.serializers import BasicProfileSerializer
from post.models import Post
from event.models import Event


def group_room_name(group_id: str) -> str:
    return f"chat_{group_id}"


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket path: /ws/chat/<group_id>/
    Protocol (JSON):
      - send message:
        {"action":"send_message","message_type":"text","content":"hi"}
      - typing:
        {"action":"typing","is_typing":true}
      - mark read:
        {"action":"mark_read"}
      - edit message
        {"action": "edit_message","message_id": "1234","content": "Updated message text"}
      - clear chat
        {"action": "clear_chat"}
      - delete for me:
        {"action": "delete_for_me", "message_ids": ["id1", "id2", "id3"]}
    """

    async def connect(self):
        self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
        self.room_name = group_room_name(self.group_id)

        ok = await self.authorized()
        if not ok:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    @database_sync_to_async
    def authorized(self) -> bool:
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        try:
            profile = get_user_profile(user)
            group = ChatGroup.objects.get(id=self.group_id)
            return is_group_member(group, profile)
        except Exception:
            return False

    async def receive_json(self, content, **kwargs):
        action = content.get("action")

        if action == "send_message":
            await self.handle_send_message(content)
        elif action == "typing":
            await self.handle_typing(content)
        elif action == "mark_read":
            await self.handle_mark_read(content)
        elif action == "edit_message":
            await self.handle_edit_message(content)
        elif action == "clear_chat":
            await self.handle_clear_chat(content)
        elif action == "delete_for_me":
            await self.handle_delete_for_me(content)

    @database_sync_to_async
    def _create_message(self, user, payload):
        profile = get_user_profile(user)
        group = ChatGroup.objects.get(id=self.group_id)
        msg = ChatMessage.objects.create(
            group=group,
            sender=profile,
            message_type=payload.get("message_type", ChatMessage.TEXT),
            content=payload.get("content", ""),
        )

        # update denormalized fields
        group.last_message = msg
        group.last_message_at = msg.created_at
        group.save(update_fields=["last_message", "last_message_at"])

        # increment unread for other members
        ChatGroupMember.objects.filter(group=group).exclude(profile=profile).update(
            unread_count=F("unread_count") + 1
        )

        # serializing for consistent response
        return ChatMessageSerializer(msg, context={"request": None, "user": user}).data
    
    @database_sync_to_async
    def _get_profile(self, user):
        return get_user_profile(user)

    @database_sync_to_async
    def _serialize_message(self, msg, user=None):
        return ChatMessageSerializer(msg, context={"request": None, "user": user}).data

    async def handle_send_message(self, payload):
        user = self.scope["user"]

        try:
            profile = await self._get_profile(user)
            group = await database_sync_to_async(ChatGroup.objects.get)(id=self.group_id)

            if payload.get("message_type") == MessageType.POST:
                post_id = payload.get("post_id")
                if not post_id:
                    raise ValueError("post_id required for post message")

                post = await database_sync_to_async(Post.objects.get)(id=post_id)

                msg = await database_sync_to_async(ChatMessage.objects.create)(
                    group=group,
                    sender=profile,
                    message_type=MessageType.POST,
                    shared_post=post,
                )

            elif payload.get("message_type") == MessageType.EVENT:
                event_id = payload.get("event_id")
                if not event_id:
                    raise ValueError("event_id required for event message")

                event = await database_sync_to_async(Event.objects.get)(id=event_id)

                msg = await database_sync_to_async(ChatMessage.objects.create)(
                    group=group,
                    sender=profile,
                    message_type=MessageType.EVENT,
                    shared_event=event,
                )

            else:
                # fallback to normal message (text/media/etc.)
                data = await self._create_message(user, payload)
                msg = await database_sync_to_async(ChatMessage.objects.get)(id=data["id"])

            # serialize consistently
            serialized = await self._serialize_message(msg, user)

            # broadcast to group
            await self.channel_layer.group_send(
                self.room_name,
                {"type": "chat.message", "data": serialized}
            )

            # update active chats sidebar
            members = await database_sync_to_async(
                list
            )(ChatGroupMember.objects.filter(group=group).values_list("profile_id", flat=True))
            await asyncio.gather(
                *[async_broadcast_active_chats_update(pid) for pid in members]
            )

        except Exception as e:
            await self.send_json({"type": "error", "message": f"{str(e)}"})

    async def chat_message(self, event):
        await self.send_json({"type": "message", "data": event["data"]})

    async def handle_typing(self, payload):
        user = self.scope["user"]
        profile = get_user_profile(user)
        data = {
            "profile": BasicProfileSerializer(profile).data,
            "group_id": self.group_id,
            "is_typing": bool(payload.get("is_typing")),
            "at": timezone.now().isoformat(),
        }

        # 1. Broadcast to members inside the chat
        await self.channel_layer.group_send(
            self.room_name,
            {"type": "chat.typing", "data": data}
        )

        # 2. Also notify each member’s active chats sidebar
        members = await database_sync_to_async(list)(
            ChatGroupMember.objects.filter(group_id=self.group_id).values_list("profile_id", flat=True)
        )
        await asyncio.gather(
            *[
                self.channel_layer.group_send(
                    f"active_chats_{pid}",
                    {"type": "active_chats.typing", "data": data}
                )
                for pid in members
            ]
        )

    async def chat_typing(self, event):
        await self.send_json({"type": "typing", "data": event["data"]})

    @database_sync_to_async
    def _mark_read(self, user):
        profile = user.profile
        group = ChatGroup.objects.get(id=self.group_id)

        unseen_messages = ChatMessage.objects.filter(
            group=group
        ).exclude(sender=profile).exclude(
            receipts__user=profile
        )

        now = timezone.now()
        receipts = []
        for msg in unseen_messages:
            receipt = MessageReceipt.objects.create(
                message=msg,
                user=profile,
                is_seen=True,
                seen_at=now
            )
            receipts.append({
                "message_id": msg.id,
                "profile_id": profile.id,
                "seen_at": now.isoformat(),
            })

        # also reset unread counter
        ChatGroupMember.objects.filter(group=group, profile=profile).update(
            unread_count=0, last_read_at=now
        )

        return receipts


    async def handle_mark_read(self, payload):
        user = self.scope["user"]
        try:
            receipts = await self._mark_read(user)
            if receipts:
                # broadcast receipts to everyone in the group
                await self.channel_layer.group_send(
                    self.room_name,
                    {"type": "chat.read", "data": receipts}
                )
                
                # update active chats only for THIS user
                await async_broadcast_active_chats_update(user.profile.id)
        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})

    async def chat_read(self, event):
        # Send receipts to client
        await self.send_json({"type": "read", "data": event["data"]})
        
    async def chat_message_deleted(self, event):
        # Send to connected clients
        await self.send_json({
            "action": "message_deleted",
            "message_id": event["message_id"],
            "group_id": event["group_id"],
        })
    
    @database_sync_to_async
    def _edit_message(self, user, payload):
        profile = get_user_profile(user)
        msg_id = payload.get("message_id")
        new_content = payload.get("content", "").strip()

        if not msg_id or not new_content:
            raise ValueError("message_id and content required")

        try:
            msg = ChatMessage.objects.get(id=msg_id, sender=profile)
        except ChatMessage.DoesNotExist:
            raise ValueError("Message not found or not yours")

        msg.mark_as_edited(new_content)
        return ChatMessageSerializer(msg, context={"request": None}).data

    async def handle_edit_message(self, payload):
        user = self.scope["user"]
        try:
            data = await self._edit_message(user, payload)
            # broadcast edit event
            await self.channel_layer.group_send(
                self.room_name,
                {"type": "chat.message_edited", "data": data}
            )
             # update active chats sidebar
            group = await database_sync_to_async(ChatGroup.objects.get)(id=self.group_id)
            members = await database_sync_to_async(list)(
                ChatGroupMember.objects.filter(group=group).values_list("profile_id", flat=True)
            )
            await asyncio.gather(*[async_broadcast_active_chats_update(pid) for pid in members])
        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})

    async def chat_message_edited(self, event):
        await self.send_json({"type": "message_edited", "data": event["data"]})
    
    @database_sync_to_async
    def _clear_chat(self, user):
        profile = get_user_profile(user)
        group = ChatGroup.objects.get(id=self.group_id)

        ChatClear.objects.update_or_create(
            profile=profile, group=group,
            defaults={"cleared_at": timezone.now()}
        )
        
        ChatGroupMember.objects.filter(group=group, profile=profile).update(
            unread_count=0, last_read_at=timezone.now()
        )

        return {"group_id": str(group.id), "cleared_at": timezone.now().isoformat()}

    async def handle_clear_chat(self, payload):
        user = self.scope["user"]
        try:
            data = await self._clear_chat(user)
            # only notify THIS user (not the whole group!)
            await self.send_json({"type": "chat_cleared", "data": data})
        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})
    
    @database_sync_to_async
    def _delete_for_me_bulk(self, user, payload):
        profile = get_user_profile(user)
        message_ids = payload.get("message_ids", [])

        if not message_ids or not isinstance(message_ids, list):
            raise ValueError("message_ids (list) required")

        # Ensure messages belong to this group
        msgs = ChatMessage.objects.filter(
            id__in=message_ids,
            group_id=self.group_id
        )

        if not msgs.exists():
            raise ValueError("No valid messages found in this chat")

        now = timezone.now()
        deleted = []

        for msg in msgs:
            DeleteMessage.objects.update_or_create(
                profile=profile,
                message=msg,
                defaults={"deleted_at": now}
            )
            deleted.append({
                "message_id": str(msg.id),
                "group_id": str(msg.group_id),
                "deleted_at": now.isoformat(),
            })

        return deleted

    async def handle_delete_for_me(self, payload):
        user = self.scope["user"]
        try:
            data = await self._delete_for_me_bulk(user, payload)

            # Notify only THIS user
            await self.send_json({
                "type": "messages_deleted_for_me",
                "data": data
            })
            
            # Recalculate sidebar ONLY for this user
            profile = await database_sync_to_async(get_user_profile)(user)
            await async_broadcast_active_chats_update(profile.id)

        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})


class ActiveChatsConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket path: /ws/active-chats/
    Sends THIS USER's active chats list in real time.
    """

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4403)
            return


        self.profile = await self._get_profile(user)

        # each user gets their own group
        self.group_name = f"active_chats_{self.profile.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # send initial data
        await self.send_active_chats()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _get_profile(self, user):
        return get_user_profile(user)

    @database_sync_to_async
    def _get_active_chats(self):
        qs = (
            ChatGroupMember.objects
            .filter(profile=self.profile, group__last_message__isnull=False)
            .select_related(
                "group", "group__group",
                "group__last_message", "group__last_message__sender"
            )
            .prefetch_related("group__memberships__profile")  # <— key optimization
            .order_by("-group__last_message__created_at", "-group__created_at")
        )

        serializer = ChatGroupMiniSerializer(
            qs, many=True, context={"profile": self.profile}
        )
        total_unread_chats = ChatGroupMember.objects.filter(
            profile=self.profile,
            unread_count__gt=0,
            group__last_message__isnull=False
        ).count()

        return {
            "chats": serializer.data,
            "total_unread_chats": total_unread_chats,
        }

    async def send_active_chats(self):
        data = await self._get_active_chats()
        await self.send_json({"type": "active_chats", "data": data})

    async def active_chats_update(self, event):
        await self.send_active_chats()
    
    async def active_chats_typing(self, event):
        await self.send_json({
            "type": "typing",
            "data": event["data"]
        })
        
    async def presence_update(self, event):
        await self.send_json({
            "type": "presence_update",
            "data": event["data"]
        })


class PresenceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4403)
            return

        self.profile = await database_sync_to_async(get_user_profile)(user)

        await self.accept()
        await self._set_online_status(True)

    async def disconnect(self, close_code):
        if hasattr(self, "profile"):
            await self._set_online_status(False)

    @database_sync_to_async
    def _set_online_status(self, is_online: bool):

        self.profile.is_online = is_online
        if not is_online:
            self.profile.last_seen = timezone.now()
        self.profile.save(update_fields=["is_online", "last_seen"])

        # broadcast presence update to active chats sidebar
        async_broadcast_presence_update(self.profile, self.profile.is_online)
