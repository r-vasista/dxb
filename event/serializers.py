# Rest Framework imports
from rest_framework import serializers

# Local imports
from event.models import (
    Event, EventAttendance, EventMedia, EventComment
)
from event.utils import generate_google_calendar_link
from profiles.models import Profile
from core.serializers import TimezoneAwareSerializerMixin

# Pyhton imports
import pytz
from pytz import timezone as pytz_timezone


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        
        
class EventCreateSerializer(TimezoneAwareSerializerMixin):
    class Meta:
        model = Event
        fields = "__all__"
        
    def validate(self, attrs):
        if attrs['end_datetime'] <= attrs['start_datetime']:
            raise serializers.ValidationError("End time must be after start time.")
        
        if attrs.get('is_online') and not attrs.get('online_link'):
            raise serializers.ValidationError("Online events must have an online link.")
        
        if not attrs.get('is_online') and not attrs.get('address'):
            raise serializers.ValidationError("Offline events must have an address.")
        
        return attrs
    

class EventListSerializer(TimezoneAwareSerializerMixin):
    host_username = serializers.CharField(source='host.username', read_only=True)
    host_profile_picture = serializers.CharField(source='host.profile_picture', read_only=True)
    co_host_username = serializers.CharField(source='co_host.username', read_only=True)
    
    class Meta:
        model = Event
        fields = "__all__"
        

class EventAttendanceSerializer(TimezoneAwareSerializerMixin):
    profile_deails = serializers.SerializerMethodField()
    calendar_link = serializers.SerializerMethodField()

    class Meta:
        model = EventAttendance
        fields = '__all__'

    def get_profile_deails(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if obj.profile.profile_picture else None,
            "status": obj.status,
        }

    def get_calendar_link(self, obj):
        return generate_google_calendar_link(obj, self.context.get('request'))
        

class EventSummarySerializer(TimezoneAwareSerializerMixin):
    calendar_link = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_datetime', 'end_datetime',
            'city', 'state', 'country', 'is_online', 'online_link', 
            'calendar_link'
        ]

    def get_calendar_link(self, obj):
        return generate_google_calendar_link(obj, self.context.get('request'))


class EventMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = ['id', 'event', 'file', 'media_type', 'title', 'description', 'is_pinned', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['media_type', 'uploaded_at']


class EventCommentSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()

    class Meta:
        model = EventComment
        fields = [
            'id', 'event', 'profile', 'content', 'parent', 
            'created_at', 'reply_count', 'is_reply'
        ]
        read_only_fields = ['id', 'event', 'profile', 'created_at', 'reply_count', 'is_reply']

    def get_profile(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if obj.profile.profile_picture else None,
        }

    def get_reply_count(self, obj):
        return obj.reply_count

    def get_is_reply(self, obj):
        return obj.is_reply
    

class EventCommentListSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    has_replies = serializers.SerializerMethodField()

    class Meta:
        model = EventComment
        fields = [
            'id', 'event', 'profile', 'content', 'parent', 
            'created_at', 'has_replies'
        ]
        read_only_fields = fields

    def get_profile(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if obj.profile.profile_picture else None,
        }

    def get_has_replies(self, obj):
        return obj.replies.exists()


class EventMediaCommentSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()

    class Meta:
        model = EventComment
        fields = [
            'id', 'event_media', 'profile', 'content', 'parent', 
            'created_at', 'reply_count', 'is_reply'
        ]
        read_only_fields = ['id', 'event_media', 'profile', 'created_at', 'reply_count', 'is_reply']

    def get_profile(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if obj.profile.profile_picture else None,
        }

    def get_reply_count(self, obj):
        return obj.reply_count

    def get_is_reply(self, obj):
        return obj.is_reply