from django.db import models

class VisibilityStatus(models.TextChoices):
    """Visibility status choices."""
    PUBLIC = 'public', 'Public'
    PRIVATE = 'private', 'Private'


class FieldType(models.TextChoices):
    """
    Simple field types for profile fields.
    """
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    FILE = 'file', 'File'
    DATE = 'date', 'Date'

class ProfileType(models.TextChoices):
    """
    Simple field types for Profiles.
    """
    ORGANIZATION = 'organization', 'Organization'
    USER = 'user', 'User'