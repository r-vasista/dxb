# Django imports
from django.utils import timezone

# Python imports
import datetime

# Rest Framework imports
from rest_framework import serializers

# Local imports
from organization.models import (
    Organization, Address, OrganizationType, IndustryType, OrganizationProfileField, OrganizationInvite, OrganizationMember
)
from organization.choices import (
    OrgInviteStatus
)
from organization.utils import validate_org_prof_fields
from user.serializers import (
    UserMiniSerializer
)


class RegisterOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        extra_kwargs = {
            'email': {'required': False},
            'address': {'required': False},
            'user': {'required': False},
            'otp': {'required': True}
        }


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'user']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'


class OrganizationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationType
        fields = '__all__'

class IndustryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndustryType
        fields = '__all__'


class OrganizationProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_public']
        extra_kwargs = {
            'field_type': {'required': True}
        }
    
    def get_value(self, obj):
        """Return the appropriate value based on field type"""
        return obj.get_value()
    
    def validate(self, data):
        validate_org_prof_fields(data)
        return data
    

class UpdateOrganizationProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'organization']
        extra_kwargs = {
            'field_type': {'required': True},
        }
    
    def get_value(self, obj):
        """Return the appropriate value based on field type"""
        return obj.get_value()
    
    def validate(self, data):
        instance = getattr(self, 'instance', None)
        if self.instance:
            data = {**self.initial_data, **data}
        if instance and 'is_active' not in data:
            data['is_active'] = instance.is_active
        validate_org_prof_fields(data, instance=self.instance)
        return data


class OrganizationInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationInvite
        fields = ['organization', 'email', 'role', 'message']

    def create(self, validated_data):

        validated_data['invited_by'] = self.context['request'].user
        validated_data['expires_at'] = timezone.now() + datetime.timedelta(days=3)

        return super().create(validated_data)
    
    def validate(self, attrs):
        """
        Custom validation to check for existing pending invites
        """
        organization = self.context.get('organization')
        email = attrs.get('email')
        
        if organization and email:
            # Check if there's already a pending invite for this email and organization
            existing_invite = OrganizationInvite.objects.filter(
                organization=organization,
                email=email,
                status=OrgInviteStatus.PENDING
            ).first()
            
            if existing_invite:
                raise serializers.ValidationError(
                    f"A pending invitation already exists for {email} in this organization."
                )
        
        return attrs


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField()

    def validate_token(self, token):
        try:
            invite = OrganizationInvite.objects.get(token=token, status=OrgInviteStatus.PENDING)
        except OrganizationInvite.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invite.")

        if invite.expires_at < timezone.now():
            raise serializers.ValidationError("Invite has expired.")
        return invite


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_data = UserMiniSerializer(read_only=True)
    class Meta:
        model = OrganizationMember
        fields = '__all__'
