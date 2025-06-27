from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import update_last_login
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from user.models import Role, Permission
from organization.models import Organization

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainSerializer):
    token_class = RefreshToken

    def validate(self, attrs):

        # Lower email while logging in
        email = attrs.get("email") or attrs.get("username")
        if email:
            attrs["email"] = email.lower()

        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Fetch profile (either directly or via organization)
        profile = getattr(self.user, "profile", None)

        if not profile and hasattr(self.user, "organization"):
            profile = getattr(self.user.organization, "profile", None)

        if profile:
            data["profile_id"] = profile.id
            data["profile_type"] = profile.profile_type
            data['username'] =  profile.username
            data['profile_picture'] = str(profile.profile_picture) if profile.profile_picture else None
        else:
            data["profile_id"] = None
            data["profile_type"] = None

        # Optional: Add more user details
        data["email"] = self.user.email
        data["user_type"] = self.user.user_type.code

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'user_type', 'full_name']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'roles']


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'type', 'description', 'content_type']


class RoleSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Role
        fields = ['id', 'name', 'organization_id', 'permissions']

    def validate(self, attrs):
        if self.instance is None and not attrs.get('permissions'):
            raise serializers.ValidationError({"permissions": "This field is required."})
        return attrs

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        org_id = validated_data.pop('organization_id', None)
        if org_id:
            organization = Organization.objects.get(id=org_id)
            validated_data['organization'] = organization
        role = Role.objects.create(**validated_data)
        role.permissions.set(permissions)
        return role
