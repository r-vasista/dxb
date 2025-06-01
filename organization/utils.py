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
    cache.set(f"otp:{email}", otp, timeout=300)
    return otp

def verify_otp(email, otp):
    saved_otp = cache.get(f"otp:{email}")
    return saved_otp == otp

def delete_otp(email):
    cache.delete(f"otp:{email}")

def validate_org_prof_fields(data):
    field_type = data.get('field_type')
    fields = [ f.value for f in FieldType]

    if field_type.lower() not in fields:
        raise ValidationError(f"{field_type} is not a valid field type")
    