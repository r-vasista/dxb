# Rest Framework imports
from rest_framework import serializers

# Local imports
from profiles.models import (
    ProfileField, Profile
)
from profiles.utils import (
    validate_profile_field_data
)
from organization.serializers import (
    OrganizationSerializer
)

class ProfileSerializer(serializers.ModelSerializer):
    profile_fields = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    friends_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'bio', 'picture', 'profile_type', 'visibility_status',
            'followers_count', 'friends_count', 'following_count',
            'organization', 'profile_fields'
        ]

    def get_profile_fields(self, obj):
        from profiles.models import ProfileField  # Prevent circular import
        fields = ProfileField.objects.filter(profile=obj)
        return ProfileFieldSerializer(fields, many=True).data

    def get_organization(self, obj):
        if obj.organization:
            return OrganizationSerializer(obj.organization).data
        return None

    

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['username', 'bio', 'picture', 'visibility_status']
        extra_kwargs = {
            'username': {'required': False}, 
        }

    # def validate_username(self, value):
    #     if Profile.objects.exclude(id=self.instance.id).filter(username=value).exists():
    #         raise serializers.ValidationError("This username is already taken.")
    #     return value


class ProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_public']
        extra_kwargs = {'field_type': {'required': True}}

    def get_value(self, obj):
        return obj.get_value()

    def validate(self, data):
        validate_profile_field_data(data)
        return data


class UpdateProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'profile']
        extra_kwargs = {'field_type': {'required': True}}

    def get_value(self, obj):
        return obj.get_value()

    def validate(self, data):
        instance = getattr(self, 'instance', None)
        if instance:
            data = {**self.initial_data, **data}
        validate_profile_field_data(data, instance=instance)
        return data
