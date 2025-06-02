from django.db import models


class PermissionType(models.TextChoices):
    """
    Simple field types for organization profile fields.
    """
    VIEW = 'view', 'View'
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'
