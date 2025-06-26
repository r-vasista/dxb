# Djangi imports
from django.core.cache import cache
from django.core.exceptions import ValidationError

# Python imports
import random

# Local imports
from organization.choices import FieldType
from organization.models import (
    OrganizationProfileField
)

def generate_otp(email):
    otp = str(random.randint(1000, 9999))
    cache.set(f"otp:{email.lower()}", otp, timeout=300)
    return otp

def verify_otp(email, otp):
    saved_otp = cache.get(f"otp:{email.lower()}")
    return saved_otp == otp

def delete_otp(email):
    cache.delete(f"otp:{email}")

def validate_org_prof_fields(data, instance=None):
    # Validate field_type is present and valid
    field_type = data.get('field_type') or (getattr(instance, 'field_type', None) if instance else None)
    if not field_type:
        raise ValidationError("field_type is required")

    valid_field_types = [f.value for f in FieldType]
    if field_type.lower() not in [ft.lower() for ft in valid_field_types]:
        raise ValidationError(f"{field_type} is not a valid field type")

    # Validate field_name
    field_name = data.get('field_name', '').strip()
    if not field_name:
        raise ValidationError("Field name cannot be empty.")

    # Validate the correct value field is set
    text_value = data.get('text_value')
    date_value = data.get('date_value')
    image_value = data.get('image_value')
    file_value = data.get('file_value')

    value_fields = {
        'text': text_value,
        'date': date_value,
        'image': image_value,
        'file': file_value,
    }

    # Ensure only the correct value field is set based on field_type
    expected_value = value_fields.get(field_type.lower()) or (getattr(instance, 'field_type', None) if instance else None)
    if not expected_value:
        raise ValidationError(f"{field_type.capitalize()} value is required for field '{field_name}'.")

    # Ensure no more than one value field is set
    value_counts = sum(1 for v in value_fields.values() if v)
    if value_counts > 1:
        raise ValidationError("Only one value field should be set based on field_type.")