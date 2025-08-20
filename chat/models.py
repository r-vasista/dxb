import uuid
from django.db import models
from django.utils import timezone

from profiles.models import Profile
from chat.choices import ChatType
from group.models import Group


class ChatGroup(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=ChatType.choices, default=ChatType.PERSONAL)
    group = models.OneToOneField(
        Group, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="chat_group"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    # for a personal chat, enforce 2 members via app logic (not DB)
    def __str__(self):
        return f"{self.type} - {self.id}"


class ChatGroupMember(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="memberships")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="chat_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)
    # per-room prefs
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("group", "profile")


class ChatMessage(models.Model):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"

    MESSAGE_TYPES = (
        (TEXT, "Text"),
        (IMAGE, "Image"),
        (FILE, "File"),
    )

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent_messages")
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default=TEXT)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="chat/files/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["group", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # lightweight denormalization for chat list ordering
        ChatGroup.objects.filter(id=self.group_id).update(last_message_at=timezone.now())


class MessageReceipt(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="receipts")
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="message_receipts")
    is_seen = models.BooleanField(default=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("message", "user")