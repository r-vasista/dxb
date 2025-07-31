# Django imports
from django.utils.text import slugify

# Rest Framework imports
from rest_framework import serializers

# Local imports
from event.models import (
    Event, EventAttendance, EventMedia, EventComment, EventMediaComment, EventMediaLike, EventMediaCommentLike, EventActivityLog
)
from event.utils import generate_google_calendar_link, is_host_or_cohost
from event.choices import (
    AttendanceStatus
)
from profiles.models import Profile
from core.serializers import TimezoneAwareSerializerMixin
from core.services import (
    get_user_profile
)
# Pyhton imports
import pytz
from pytz import timezone as pytz_timezone


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        

class EventDetailSerializer(TimezoneAwareSerializerMixin):
    host = serializers.SerializerMethodField()
    city = serializers.CharField(source='city.name', read_only=True)
    state = serializers.CharField(source='state.name', read_only=True)
    country = serializers.CharField(source='country.name', read_only=True)
    total_attendee_count = serializers.SerializerMethodField()
    interested_count = serializers.SerializerMethodField()
    not_interested_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    user_rsvp_status = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    is_host_or_cohost = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'event_type', 'status',
            'start_datetime', 'end_datetime', 'timezone',
            'is_online', 'address', 'city', 'state', 'country', 'online_link',
            'is_free', 'price', 'currency', 'event_image', 'host', 'slug', 
            'event_logo', 'total_attendee_count', 'interested_count', 'not_interested_count',
            'pending_count', 'allow_public_media', 'created_at', 'updated_at','view_count', 'user_rsvp_status',
            'updated_end_datetime', 'updated_start_datetime', 'max_attendees', 'aprove_attendees', 'show_views',
            'share_count', 'is_host_or_cohost'
        ]

    def get_host(self, obj):
        return {
            "id": obj.host.id,
            "username": obj.host.username,
            "profile_picture": obj.host.profile_picture.url if obj.host.profile_picture else None
        }
        
    def get_total_attendee_count(slef, obj):
        return int(obj.attendee_count)
    
    def get_interested_count(self, obj):
        return obj.eventattendance_set.filter(status=AttendanceStatus.INTERESTED).count()

    def get_not_interested_count(self, obj):
        return obj.eventattendance_set.filter(status=AttendanceStatus.NOT_INTERESTED).count()
    
    def get_pending_count(self, obj):
        return obj.eventattendance_set.filter(status=AttendanceStatus.PENDING).count()
    
    def get_user_rsvp_status(self, obj):
        try:
            request = self.context.get('request')
            if not request or not request.user.is_authenticated:
                return None

            user = request.user
            profile = get_user_profile(user)

            # Now check for the specific event attendance
            event_attendance = EventAttendance.objects.filter(
                profile=profile,
                event=obj
            ).first()

            if event_attendance:
                return event_attendance.status
            return None
        except Exception:
            return None
    
    def get_view_count(self, obj):
        try:
            user = self.context.get('request').user
            profile = get_user_profile(user)
            if is_host_or_cohost(obj, profile):
                return obj.view_count
            return obj.view_count if obj.show_views else None
        except:
            return None
    
    def get_is_host_or_cohost(self, obj):
        try:
            user = self.context.get('request').user
            profile = get_user_profile(user)
            return is_host_or_cohost(obj, profile)
        except:
            return None
        
        
class EventCreateSerializer(TimezoneAwareSerializerMixin):
    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = ['host']
        
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
    
    class Meta:
        model = Event
        fields = "__all__"
        

class EventAttendanceSerializer(TimezoneAwareSerializerMixin):
    profile_details = serializers.SerializerMethodField()
    calendar_link = serializers.SerializerMethodField()

    class Meta:
        model = EventAttendance
        fields = '__all__'

    def get_profile_details(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if obj.profile.profile_picture else None,
            "status": obj.status,
        }

    def get_calendar_link(self, obj):
        try:
            return generate_google_calendar_link(obj.event, self.context.get('request'))
        except Exception:
            return None
        

class EventSummarySerializer(TimezoneAwareSerializerMixin):
    calendar_link = serializers.SerializerMethodField()
    host_username = serializers.CharField(source='host.username', read_only=True)
    host_profile_picture = serializers.CharField(source='host.profile_picture', read_only=True)


    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_datetime', 'end_datetime',
            'city', 'state', 'country', 'is_online', 'online_link', 
            'calendar_link', 'slug','host_username', 'host_profile_picture',
            'event_image','event_logo', 'description'
        ]

    def get_calendar_link(self, obj):
        return generate_google_calendar_link(obj, self.context.get('request'))


class EventMediaSerializer(serializers.ModelSerializer):
    
    uploaded_by_details = serializers.SerializerMethodField()
    class Meta:
        model = EventMedia
        fields = [
                    'id', 'event', 'file', 'media_type', 'title', 'description', 'is_pinned', 'uploaded_at',
                    'uploaded_by','like_count', 'uploaded_by_host', 'uploaded_by_details'
                ]
        read_only_fields = ['media_type', 'uploaded_at', 'uploaded_by_host']
    
    def get_uploaded_by_details(self, obj):
        return {
            "id": obj.uploaded_by.id,
            "username": obj.uploaded_by.username,
            "profile_picture": obj.uploaded_by.profile_picture.url if obj.uploaded_by.profile_picture else None,
        }


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
        model = EventMediaComment
        fields = [
            'id', 'event_media', 'profile', 'content', 'parent', 
            'created_at', 'reply_count', 'is_reply','like_count'
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

class EventSerializer(serializers.ModelSerializer):
    attendee_count = serializers.IntegerField(read_only=True)
    host_username = serializers.CharField(source='host.username', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_datetime', 'end_datetime',
            'event_image', 'attendee_count', 'tags', 'description',
            'is_online', 'city', 'country', 'slug', 'event_logo', 'host_username'
        ]


class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating events.
    Allows partial updates and regenerates slug if title changes.
    """
    class Meta:
        model = Event
        # Include only fields that should be editable
        fields = [
            "title", "description", "event_type", "status",
            "start_datetime", "end_datetime", "timezone",
            "is_online", "address", "city", "state", "country", "online_link",
            "max_attendees", "is_free", "price", "currency",
            "event_image", "event_logo", "tags","slug", "aprove_attendees", "allow_public_media",
            "updated_end_datetime", "updated_start_datetime", "show_views"
        ]
        read_only_fields = ["slug", "start_datetime", "end_datetime"]
    
    def validate(self, attrs):
        start = attrs.get("updated_start_datetime", self.instance.updated_start_datetime)
        end = attrs.get("updated_end_datetime", self.instance.updated_end_datetime)

        if start and end and end <= start:
            raise serializers.ValidationError("End time must be after start time.")

        if attrs.get('is_online') and not (attrs.get('online_link') or self.instance.online_link):
            raise serializers.ValidationError("Online events must have an online link.")

        if not attrs.get('is_online') and not (attrs.get('address') or self.instance.address):
            raise serializers.ValidationError("Offline events must have an address.")

        return attrs

    def update(self, instance, validated_data):
        # Auto-regenerate slug if title is updated
        title_changed = False
        if "title" in validated_data and validated_data["title"] != instance.title:
            title_changed = True

        instance = super().update(instance, validated_data)

        # Handle slug update if title changed
        if title_changed:
            base_slug = slugify(instance.title)
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
            instance.save()

        return instance


class EventMediaLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMediaLike
        fields = '__all__'


class EventMediaCommentLikeSerializer(serializers.ModelSerializer):
    profile_username = serializers.CharField(source='profile.username', read_only=True)
    profile_picture = serializers.CharField(source='profile.profile_picture',read_only=True) 

    class Meta:
        model = EventMediaCommentLike
        fields = ['id', 'profile', 'profile_username','profile_picture', 'event_media_comment', 'created_at']


class EventActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventActivityLog
        fields = ['id', 'event', 'activity_type', 'timestamp']
        read_only_fields = ['id', 'timestamp']