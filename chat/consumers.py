import json
import asyncio

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import F

from chat.models import ChatGroup, ChatMessage, ChatGroupMember, MessageReceipt
from chat.utils import is_group_member, broadcast_active_chats_update, async_broadcast_active_chats_update
from chat.serializers import ChatMessageSerializer, ChatGroupMiniSerializer
from core.services import get_user_profile


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
        return ChatMessageSerializer(msg, context={"request": None}).data

    async def handle_send_message(self, payload):
        user = self.scope["user"]
        try:
            data = await self._create_message(user, payload)
            # broadcast
            await self.channel_layer.group_send(
                self.room_name,
                {"type": "chat.message", "data": data}
            )
            # update active chats for all members
            group = await database_sync_to_async(ChatGroup.objects.get)(id=self.group_id)
            members = await database_sync_to_async(
                list
            )(ChatGroupMember.objects.filter(group=group).values_list("profile_id", flat=True))
            await asyncio.gather(
                *[async_broadcast_active_chats_update(pid) for pid in members]
            )
        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})

    async def chat_message(self, event):
        await self.send_json({"type": "message", "data": event["data"]})

    async def handle_typing(self, payload):
        user = self.scope["user"]
        data = {
            "profile_id": user.profile.id,
            "username": user.profile.username,
            "is_typing": bool(payload.get("is_typing")),
            "at": timezone.now().isoformat(),
        }
        await self.channel_layer.group_send(self.room_name, {"type": "chat.typing", "data": data})

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
