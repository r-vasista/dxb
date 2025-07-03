# Rest Framework imports
from rest_framework import serializers

# Local imports
from event.models import Event, City, State, Country
from profiles.models import Profile  # Adjust as per your project
from core.serializers import TimezoneAwareSerializerMixin

# Pyhton imports
import pytz
from pytz import timezone as pytz_timezone

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
    class Meta:
        model = Event
        fields = "__all__"