# serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_id = serializers.SerializerMethodField()
    sender_profile_picture = serializers.SerializerMethodField()
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    post_id = serializers.SerializerMethodField()
    post_slug = serializers.SerializerMethodField()

    def get_sender_id(self, obj):
        return obj.sender.id if obj.sender else None
    def get_sender_profile_picture(self, obj):
        return obj.sender.profile_picture.url if obj.sender and obj.sender.profile_picture else None
    
    def get_post_id(self, obj):
        if obj.content_type and obj.content_type.model == 'post' and obj.object_id:
            return obj.object_id
        return None
    
    def get_post_slug(self, obj):
        if obj.content_type and obj.content_type.model == 'post' and obj.object_id:
            post = obj.content_object
            return post.slug if post and hasattr(post, 'slug') else None
        return None

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
            'content_type',
            'post_id',
            'post_slug',
        ]
