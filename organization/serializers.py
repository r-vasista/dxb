# Rest Framework imports
from rest_framework import serializers

# Local imports
from organization.models import (
    Organization, Address
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


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'