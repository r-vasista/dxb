# Rest Framework imports
from rest_framework import serializers

# Local imports
from organization.models import (
    Organization, Address, OrganizationType, IndustryType, OrganizationProfileField
)
from organization.utils import validate_org_prof_fields


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
        fields = [
            'id', 'organization', 'field_name', 'field_type', 'value',
            'text_value', 'image_value', 'file_value', 'date_value',
            'is_public', 'display_order', 'description'
        ]
        read_only_fields = ['id']
    
    def get_value(self, obj):
        """Return the appropriate value based on field type"""
        return obj.get_value()
    
    def validate(self, data):
        validate_org_prof_fields(data)
        return data

class BulkOrganizationProfileFieldSerializer(serializers.Serializer):
    """Serializer for bulk creation of profile fields"""
    fields = OrganizationProfileFieldSerializer(many=True)
    
    def validate_fields(self, fields_data):
        """Validate that field names are unique within the batch"""
        field_names = [field.get('field_name') for field in fields_data]
        if len(field_names) != len(set(field_names)):
            raise serializers.ValidationError(
                "Field names must be unique within the same organization."
            )
        return fields_data
    
    def create(self, validated_data):
        """Create multiple profile fields at once"""
        organization_id = validated_data['organization_id']
        fields_data = validated_data['fields']
        
        created_fields = []
        for field_data in fields_data:
            field_data['organization_id'] = organization_id
            serializer = OrganizationProfileFieldSerializer(data=field_data)
            serializer.is_valid(raise_exception=True)
            created_fields.append(serializer.save())
        
        return created_fields
