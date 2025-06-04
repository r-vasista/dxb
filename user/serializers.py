from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import Role, Permission
from organization.models import Organization

User = get_user_model()

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
