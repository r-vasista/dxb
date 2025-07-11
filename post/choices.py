from django.db import models

class PostStatus(models.TextChoices):
    """Status of posts for moderation and publishing."""
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'
    REMOVED = 'removed', 'Removed'
    DRAFT = 'draft', 'Draft' 


class PostVisibility(models.TextChoices):
    """Visibility settings for posts."""
    PUBLIC = 'public', 'Public'
    FOLLOWERS_ONLY = 'followers', 'Followers Only'
    PRIVATE = 'private', 'Private',
    FRIENDS_ONLY = 'friends', 'Friends Only'


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