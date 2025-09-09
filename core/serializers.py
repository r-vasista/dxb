import pytz
from dateutil import parser
from rest_framework import serializers
from django.db.models.fields import DateTimeField
from datetime import datetime
from django.contrib.contenttypes.models import ContentType


from core.models import (
    Country, State, City, WeeklyChallenge,UpcomingFeature, FeatureStep,HashTag,Report
)

# class TimezoneAwareSerializerMixin(serializers.ModelSerializer):
#     """
#     Converts all DateTimeFields between UTC <-> User's timezone
#     - to_representation: always show in user's timezone (ISO 8601)
#     - to_internal_value: always save as UTC in DB
#     """

#     def get_user_timezone(self):
#         request = self.context.get("request")
#         if request and hasattr(request, "user"):
#             tz_str = getattr(request.user, "timezone", "UTC")
#         else:
#             tz_str = "UTC"

#         try:
#             return pytz.timezone(tz_str)
#         except pytz.UnknownTimeZoneError:
#             return pytz.UTC

#     def to_representation(self, instance):
#         rep = super().to_representation(instance)
#         user_tz = self.get_user_timezone()

#         for field_name, field in self.fields.items():
#             if isinstance(field, serializers.DateTimeField) and rep.get(field_name):
#                 try:
#                     value = getattr(instance, field_name)
#                     if value:
#                         rep[field_name] = value.astimezone(user_tz).isoformat()
#                 except Exception:
#                     pass  # failsafe
#         return rep

#     def to_internal_value(self, data):
#         validated = super().to_internal_value(data)
#         user_tz = self.get_user_timezone()

#         for field_name, field in self.fields.items():
#             if isinstance(field, serializers.DateTimeField) and validated.get(field_name):
#                 dt = validated[field_name]

#                 try:
#                     # If naive → assume user timezone
#                     if dt.tzinfo is None:
#                         dt = user_tz.localize(dt)
#                     else:
#                         # Normalize to user tz first
#                         dt = dt.astimezone(user_tz)

#                     # Always store in UTC
#                     validated[field_name] = dt.astimezone(pytz.UTC)

#                 except Exception:
#                     pass  # failsafe

#         return validated

class TimezoneAwareSerializerMixin(serializers.ModelSerializer):
    """
    Debug version: prints conversion steps
    """

    def get_user_timezone(self):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tz_str = getattr(request.user, "timezone", "UTC")
        else:
            tz_str = "UTC"

        try:
            tz = pytz.timezone(tz_str)
            print(f"[DEBUG] Using user timezone: {tz_str}")
            return tz
        except pytz.UnknownTimeZoneError:
            print(f"[DEBUG] Unknown timezone {tz_str}, defaulting to UTC")
            return pytz.UTC

    def to_representation(self, instance):
        print('REPRESENTING')
        rep = super().to_representation(instance)
        user_tz = self.get_user_timezone()

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and rep.get(field_name):
                try:
                    value = getattr(instance, field_name)
                    if value:
                        print(f"[DEBUG] Serializing field '{field_name}' = {value} (UTC)")
                        rep[field_name] = value.astimezone(user_tz).isoformat()
                        print(f"[DEBUG] → Converted to {rep[field_name]} (user tz)")
                except Exception as e:
                    print(f"[DEBUG] Serialization failed for {field_name}: {e}")
        return rep

    def to_internal_value(self, data):
        print("SAVING")
        validated = super().to_internal_value(data)
        user_tz = self.get_user_timezone()

        for field_name, field in self.fields.items():
            if isinstance(field, serializers.DateTimeField) and data.get(field_name):
                raw = data[field_name]
                try:
                    if isinstance(raw, str):
                        dt = parser.parse(raw)

                        # 👇 FIX: if no tzinfo in raw string, assume user's timezone
                        if dt.tzinfo is None:
                            dt = user_tz.localize(dt)
                            print(f"[DEBUG] Localized naive '{field_name}' → {dt}")
                        else:
                            dt = dt.astimezone(user_tz)
                            print(f"[DEBUG] Normalized aware '{field_name}' → {dt}")
                    else:
                        dt = field.to_internal_value(raw)
                        if dt.tzinfo is None:
                            dt = user_tz.localize(dt)

                    # Always save as UTC
                    validated[field_name] = dt.astimezone(pytz.UTC)
                    print(f"[DEBUG] Stored '{field_name}' in UTC → {validated[field_name]}")

                except Exception as e:
                    print(f"[DEBUG] Conversion failed for {field_name}: {e}")
        print('SAVING WIHT DATA: ', validated)
        return validated

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