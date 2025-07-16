# Rest Framework imports
from rest_framework import serializers

# Local imports
from event.models import Event, EventAttendance, EventMedia
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
        

class EventAttendanceSerializer(serializers.ModelSerializer):
    profile_deails = serializers.SerializerMethodField()
    
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
        

class EventSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'start_datetime', 'end_datetime',
            'city', 'state', 'country', 'is_online', 'online_link'
        ]


class EventMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventMedia
        fields = ['id', 'event', 'file', 'media_type', 'title', 'description', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['media_type', 'uploaded_at']