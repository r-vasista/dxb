from django.db import models

class OrganizationStatus(models.TextChoices):
    """Organization status choices."""
    PENDING = 'pending', 'Pending Verification'
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    INACTIVE = 'inactive', 'Inactive'


class VisibilityStatus(models.TextChoices):
    """Visibility status choices."""
    PUBLIC = 'public', 'Public'
    PRIVATE = 'private', 'Private'