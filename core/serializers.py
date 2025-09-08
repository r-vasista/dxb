import pytz
from rest_framework import serializers
from django.db.models.fields import DateTimeField
from datetime import datetime
from django.contrib.contenttypes.models import ContentType


from core.models import (
    Country, State, City, WeeklyChallenge,UpcomingFeature, FeatureStep,HashTag,Report
)

class TimezoneAwareSerializerMixin(serializers.ModelSerializer):
    """
    Converts all DateTimeFields from UTC → user's timezone in output,
    and from user's timezone → UTC in input (write).
    Works in both API views (context['request']) and Consumers (context['user']).
    """

    def _get_user_timezone(self):
        # Try request first
        request = self.context.get("request")
        if request and hasattr(request, "user") and getattr(request.user, "timezone", None):
            user_tz_str = request.user.timezone
        else:
            # Fall back to consumer user in context
            user = self.context.get("user")
            if user and getattr(user, "timezone", None):
                user_tz_str = user.timezone
            else:
                user_tz_str = "UTC"

        try:
            return pytz.timezone(user_tz_str)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user_tz = self._get_user_timezone()

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and rep.get(field_name):
                try:
                    value = getattr(instance, field_name)
                    if value:
                        rep[field_name] = value.astimezone(user_tz).isoformat()
                except Exception:
                    pass
        return rep

    def to_internal_value(self, data):
        user_tz = self._get_user_timezone()

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and field_name in data:
                try:
                    raw = data[field_name]

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

                except Exception:
                    pass

        

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



class FeatureStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureStep
        fields = '__all__'
    
    def create(self, validated_data):
        steps_data = validated_data.pop('steps', [])
        feature = UpcomingFeature.objects.create(**validated_data)
        for step in steps_data:
            FeatureStep.objects.create(feature=feature, **step)
        return feature

class UpcomingFeatureSerializer(serializers.ModelSerializer):
    steps = FeatureStepSerializer(many=True, read_only=True)

    class Meta:
        model = UpcomingFeature
        fields = ['id', 'title', 'description', 'status', 'steps', 'created_at']

class HashTagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)
    class Meta:
        model = HashTag
        fields = ['name'] 

class ReportSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(write_only=True)  # e.g. "post"
    object_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "content_type",
            "object_id",
            "reason",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        model_name = attrs.get("content_type")
        object_id = attrs.get("object_id")

        # Ensure content_type exists
        try:
            content_type = ContentType.objects.get(model=model_name)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"content_type": "Invalid content type."})

        # Ensure object exists
        model_class = content_type.model_class()
        if not model_class.objects.filter(id=object_id).exists():
            raise serializers.ValidationError(
                {"object_id": f"{model_name} with this id does not exist."}
            )

        attrs["content_type"] = content_type
        return attrs

    def create(self, validated_data):
        # Reporter, ip, user_agent will be passed from view
        return Report.objects.create(**validated_data)