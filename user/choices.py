from django.db import models


class PermissionType(models.TextChoices):
    """
    Simple field types for organization profile fields.
    """
    VIEW = 'view', 'View'
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    DELETE = 'delete', 'Delete'

class PermissionScope(models.TextChoices):
    """
    Choices for scope of the permissions
    """
    GLOBAL = 'global', 'Global'
    ORGANIZATION = 'organization', 'Organization'
    ADMIN = 'admin', 'System Admin'
    

class ProviderChoices(models.TextChoices):
    """
    Choices for scope of the permissions
    """
    GOOGLE = 'google', 'Google'