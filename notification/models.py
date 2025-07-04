# Django imports
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

# Local imports
from user.models import CustomUser
from profiles.models import Profile


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Accept'),
        ('tag', 'Tag'),
        ('mention', 'Mention'),
        ('share', 'Share'),
        ('post_create', 'Post Create'),
    ]
    
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    
    # Generic foreign key to link to any model (Post, Comment, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.notification_type}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()

# Create your models here.
