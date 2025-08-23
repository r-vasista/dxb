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


class StaticFieldType(models.TextChoices):
    TEXT = 'text', 'Text'
    DATE = 'date', 'Date'
    IMAGE = 'image', 'Image'
    FILE = 'file', 'File'
    NUMBER = 'number', 'Number'
    EMAIL = 'email', 'Email'
    URL = 'url', 'URL'
    BOOLEAN = 'boolean', 'Boolean'
    TEXTAREA = 'textarea', 'Textarea'


class DocumentType(models.TextChoices):
        ID_PROOF = "id_proof", "ID Proof"
        ADDRESS_PROOF = "address_proof", "Address Proof"
        PHOTO = "photo", "Photo"
        OTHER = "other", "Other"

class VerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
