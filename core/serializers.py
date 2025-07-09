import pytz
from rest_framework import serializers
from django.db.models.fields import DateTimeField
from datetime import datetime

from core.models import (
    Country, State, City, WeeklyChallenge
)

class TimezoneAwareSerializerMixin(serializers.ModelSerializer):
    """
    Converts all DateTimeFields from UTC → user's timezone in output,
    and from user's timezone → UTC in input (write).
    """

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        user_tz_str = getattr(request.user, 'timezone', 'UTC') if request and hasattr(request, 'user') else 'UTC'
        try:
            user_tz = pytz.timezone(user_tz_str)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and rep.get(field_name):
                try:
                    value = getattr(instance, field_name)
                    if value:
                        rep[field_name] = value.astimezone(user_tz).isoformat()
                except Exception:
                    pass  # Failsafe
        return rep

    def to_internal_value(self, data):
        """
        Converts datetime inputs from user's timezone → UTC
        """
        request = self.context.get('request')
        user_tz_str = getattr(request.user, 'timezone', 'UTC') if request and hasattr(request, 'user') else 'UTC'

        try:
            user_tz = pytz.timezone(user_tz_str)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and field_name in data:
                try:
                    raw = data[field_name]

                    # Parse raw string manually to ignore DRF’s UTC parsing
                    if isinstance(raw, str):
                        naive_dt = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S')
                        local_dt = user_tz.localize(naive_dt)
                        data[field_name] = local_dt.astimezone(pytz.UTC)
                    else:
                        dt = field.to_internal_value(raw)
                        if dt.tzinfo is None:
                            dt = user_tz.localize(dt)
                        else:
                            dt = dt.astimezone(user_tz)
                        data[field_name] = dt.astimezone(pytz.UTC)

                except Exception as e:
                    pass

        return super().to_internal_value(data)
        

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code']

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name', 'code', 'country']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'country', 'latitude', 'longitude']


class WeeklyChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyChallenge
        fields = '__all__'