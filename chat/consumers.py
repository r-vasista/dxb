import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import ChatGroup, ChatMessage, ChatGroupMember
from .utils import is_group_member


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
            profile = user.profile
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
        profile = user.profile
        group = ChatGroup.objects.select_for_update().get(id=self.group_id)
        msg = ChatMessage.objects.create(
            group=group,
            sender=profile,
            message_type=payload.get("message_type", ChatMessage.TEXT),
            content=payload.get("content", ""),
        )
        return {
            "id": msg.id,
            "group": str(group.id),
            "sender": {"id": profile.id, "username": profile.username},
            "message_type": msg.message_type,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }

    async def handle_send_message(self, payload):
        user = self.scope["user"]
        try:
            data = await self._create_message(user, payload)
            # broadcast
            await self.channel_layer.group_send(
                self.room_name,
                {"type": "chat.message", "data": data}
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
        membership = ChatGroupMember.objects.get(group_id=self.group_id, profile=profile)
        membership.last_read_at = timezone.now()
        membership.save(update_fields=["last_read_at"])
        return {
            "profile_id": profile.id,
            "last_read_at": membership.last_read_at.isoformat(),
        }

    async def handle_mark_read(self, payload):
        user = self.scope["user"]
        try:
            data = await self._mark_read(user)
            await self.channel_layer.group_send(self.room_name, {"type": "chat.read", "data": data})
        except Exception as e:
            await self.send_json({"type": "error", "message": str(e)})

    async def chat_read(self, event):
        await self.send_json({"type": "read", "data": event["data"]})
