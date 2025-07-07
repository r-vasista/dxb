# serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'message',
            'is_read',
            'created_at',
            'sender_username',
            'recipient_username',
            'object_id',
            'content_type'
        ]
