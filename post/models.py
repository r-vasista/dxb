# Django imports
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone

# Local import
from core.models import BaseModel
from organization.models import Organization
from post.choices import (
    PostStatus, PostVisibility, MediaType, ReactionType
)

User = get_user_model()

class Post(BaseModel):
    """
    Main post model for organizations to share content.
    """
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='posts',
        null=True,
        blank=True,
    )
    organization_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='org_user_posts',
        help_text="User who created the post on behalf of the organization",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='user_posts',
        help_text="User who created the post on behalf of the organization",
        null=True,
        blank=True,
    )
    
    # Content fields
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    caption = models.TextField(blank=True)
    
    # Metadata
    slug = models.SlugField(max_length=150, blank=True)
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.PUBLISHED
    )
    visibility = models.CharField(
        max_length=20,
        choices=PostVisibility.choices,
        default=PostVisibility.PUBLIC
    )
    
    # Engagement metrics (denormalized for performance)
    reaction_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # SEO and sharing
    meta_description = models.TextField(max_length=160, blank=True)
    
    # Moderation
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    allow_reactions = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.organization or self.user}: {self.title or self.content[:50]}"

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = self._generate_unique_slug()
        
        # Set published_at when status changes to published
        if self.status == PostStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        
        while Post.objects.filter(
            organization=self.organization,
            slug=slug,
            status=PostStatus.PUBLISHED
        ).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        
        return slug


class PostMedia(BaseModel):
    """
    Media attachments for posts (images, videos, documents).
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='posts/media/')
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    order = models.PositiveSmallIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']


class PostReaction(BaseModel):
    """
    User reactions to posts (like, love, support, etc.).
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
        default=ReactionType.LIKE
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.username} {self.reaction_type} {self.post}"


class Comment(BaseModel):
    """
    Comments on posts with threading support.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    content = models.TextField()
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    
    # Engagement
    like_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['parent', 'created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post}"

    @property
    def is_reply(self):
        return self.parent is not None


class CommentLike(BaseModel):
    """
    Likes on comments.
    """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['comment', 'user']
