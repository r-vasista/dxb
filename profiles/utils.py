# Rest Framework imports
from rest_framework.exceptions import ValidationError

# Django imports 
from django.core.exceptions import ValidationError as  d_ValidationError

# Python imports
import random
import re

# Local imports
from profiles.choices import FieldType


def validate_profile_field_data(data, instance=None):
    # Field type resolution
    field_type = data.get('field_type') or (getattr(instance, 'field_type', None) if instance else None)
    if not field_type:
        raise ValidationError("field_type is required")

    valid_field_types = [f.value for f in FieldType]
    if field_type.lower() not in [ft.lower() for ft in valid_field_types]:
        raise ValidationError(f"{field_type} is not a valid field type")

    # Field name check
    field_name = data.get('field_name', '').strip()
    if not field_name:
        raise ValidationError("field_name cannot be empty.")

    # Determine values from data or fallback to instance if not present in data
    text_value = data.get('text_value') or (getattr(instance, 'text_value', None) if instance else None)
    date_value = data.get('date_value') or (getattr(instance, 'date_value', None) if instance else None)
    image_value = data.get('image_value') or (getattr(instance, 'image_value', None) if instance else None)
    file_value = data.get('file_value') or (getattr(instance, 'file_value', None) if instance else None)

    value_fields = {
        'text': text_value,
        'date': date_value,
        'image': image_value,
        'file': file_value,
    }

    # Ensure correct field is set for field_type
    selected_value = value_fields.get(field_type.lower())
    if not selected_value:
        raise ValidationError(f"{field_type.capitalize()} value is required for field '{field_name}'.")

    # Ensure only one value field is set
    set_field_count = sum(1 for val in value_fields.values() if val)
    if set_field_count > 1:
        raise ValidationError("Only one value field should be set based on field_type.")

def validate_username_format(value):
    """
    Only allows lowercase letters, digits, underscores.
    No spaces, no special characters.
    """
    if not re.fullmatch(r'^[a-z0-9_]+$', value):
        raise d_ValidationError(
            "Username can only contain lowercase letters, numbers, and underscores (_), and no spaces or special characters."
        )