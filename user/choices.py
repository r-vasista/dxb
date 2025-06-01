from django.db import models


class PermissionType(models.TextChoices):
    """
    Simple field types for organization profile fields.
    """
    VIEW = 'view', 'View'
    CREATE = 'create', 'Create'
    EDIT = 'edit', 'Edit'
    DELETE = 'delete', 'Delete'
