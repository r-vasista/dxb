import uuid
from django.db import models
from django.utils import timezone

from profiles.models import Profile
from chat.choices import ChatType, MessageType
from group.models import Group, GroupPost
from post.models import Post
from event.models import Event, EventMedia


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
    last_message = models.ForeignKey(
        "ChatMessage", on_delete=models.SET_NULL, null=True, blank=True, related_name="msg_chat_group"
    )

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
    unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("group", "profile")


class ChatMessage(models.Model):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    POST = "post"
    EVENT = "event"
    GROUP_POST = "group_post"
    EVENT_MEDIA = "event_media"

    MESSAGE_TYPES = (
        (TEXT, "Text"),
        (IMAGE, "Image"),
        (FILE, "File"),
        (POST, "Post"),
        (EVENT, "Event"),
        (GROUP_POST, "GroupPost"),
        (EVENT_MEDIA, "EventMedia"),
    )

    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent_messages")

    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default=TEXT)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="chat/files/", blank=True, null=True)

    shared_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.SET_NULL, related_name="post_in_messages")
    shared_event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL, related_name="event_in_messages")
    shared_group_post = models.ForeignKey(GroupPost, null=True, blank=True, on_delete=models.SET_NULL, related_name="group_post_in_messages")
    shared_event_media = models.ForeignKey(EventMedia, null=True, blank=True, on_delete=models.SET_NULL, related_name="event_media_in_messages")

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["group", "-created_at"]),
        ]

    def mark_as_edited(self, new_content):
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=["content", "is_edited", "edited_at", "updated_at"])

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
        

class ChatClear(models.Model):
    """
    Tracks the point at which a user cleared a chat.
    Messages older than `cleared_at` won't be shown to that user.
    """
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="cleared_chats")
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="clears")
    cleared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("profile", "group")


class DeleteMessage(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="deletions")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="deleted_messages")
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "profile")


class ScheduleMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="scheduled_messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="scheduled_messages")
    message_type = models.CharField(max_length=20, default=ChatMessage.TEXT)
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="chat/scheduled/", blank=True, null=True)
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.sender} to {self.group} at {self.scheduled_at}'
