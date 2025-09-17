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


class FieldType(models.TextChoices):
    """
    Simple field types for organization profile fields.
    """
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    FILE = 'file', 'File'
    DATE = 'date', 'Date'


class OrgInviteStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class PostStatus(models.TextChoices):
    """Status of posts for moderation and publishing."""
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'
    FLAGGED = 'flagged', 'Flagged'
    REMOVED = 'removed', 'Removed'


class PostVisibility(models.TextChoices):
    """Visibility settings for posts."""
    PUBLIC = 'public', 'Public'
    FOLLOWERS_ONLY = 'followers', 'Followers Only'
    PRIVATE = 'private', 'Private'


class ReactionType(models.TextChoices):
    """Types of reactions users can give to posts."""
    LIKE = 'like', 'Like'
    LOVE = 'love', 'Love'
    SUPPORT = 'support', 'Support'
    CELEBRATE = 'celebrate', 'Celebrate'
    INSIGHTFUL = 'insightful', 'Insightful'


class MediaType(models.TextChoices):
    """Types of media in post"""
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'