# serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_id = serializers.SerializerMethodField()
    sender_profile_picture = serializers.SerializerMethodField()
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    def get_sender_id(self, obj):
        return obj.sender.id if obj.sender else None
    def get_sender_profile_picture(self, obj):
        return obj.sender.profile_picture.url if obj.sender and obj.sender.profile_picture else None

    class Meta:
        model = Notification
        fields = [
            'id',
            'sender_id',
            'sender_profile_picture',
            'notification_type',
            'message',
            'is_read',
            'created_at',
            'sender_username',
            'recipient_username',
            'object_id',
            'content_type'
        ]
