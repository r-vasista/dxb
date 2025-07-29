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
from profiles.models import (
    Profile
)
from core.models import (
    Country, State, City
)
from core.utils import (
    normalize_name
)


User = get_user_model()

class CustomArtType(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower()
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ArtType(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower()
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)



class Post(BaseModel):
    """
    A Post authored by a Profile (either an individual user or an org profile),
    with `created_by` pointing at the actual User who made the request.
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='posts',
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_posts',
        help_text="The User (org-admin or individual) who actually created the post."
    )

    # Content
    title = models.TextField()
    content = models.TextField(blank=True)
    caption = models.TextField(blank=True)
    art_types = models.ManyToManyField(ArtType, related_name='art_type_posts', blank=True)
    custom_art_types = models.ManyToManyField(CustomArtType, related_name='custom_art_type_posts', blank=True)

    # Slug & Status
    slug = models.SlugField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.PUBLISHED)
    visibility = models.CharField(max_length=20, choices=PostVisibility.choices, default=PostVisibility.PUBLIC)

    # Gallery order
    gallery_order = models.PositiveIntegerField(blank=True, null=True)

    # Engagement metrics (denormalized)
    reaction_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    # SEO & Moderation
    meta_description = models.TextField(max_length=160, blank=True)
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    allow_reactions = models.BooleanField(default=True)

    city = models.ForeignKey(City, blank=True, null=True, on_delete=models.SET_NULL)
    state = models.ForeignKey(State, blank=True, null=True, on_delete=models.SET_NULL)
    country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.SET_NULL)


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        author = self.profile.username or str(self.profile)
        return f"{author}: {self.title or self.content[:50]}"

    def save(self, *args, **kwargs):
        # Auto-generate slug per profile
        if not self.slug and self.title:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Post.objects.filter(profile=self.profile, slug=slug, status=PostStatus.PUBLISHED).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug

        # Set published_at when first going live
        if self.status == PostStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        if not self.gallery_order and self.profile:
            max_order = Post.objects.filter(profile=self.profile).aggregate(
                max_order=models.Max('gallery_order')
            )['max_order'] or 0
            self.gallery_order = max_order + 1

        super().save(*args, **kwargs)


class PostMedia(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='posts/media/')
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']


class PostReaction(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20, choices=ReactionType.choices, default=ReactionType.LIKE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['post', 'profile']
        indexes = [models.Index(fields=['post', 'reaction_type'])]


class SharePost(BaseModel):
    post=models.ForeignKey(Post, on_delete=models.CASCADE,related_name="share")
    profile=models.ForeignKey(Profile,on_delete=models.CASCADE,related_name="profile_share")


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)


    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['parent', 'created_at']),
            models.Index(fields=['profile', '-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.profile} on {self.post}"


class CommentLike(BaseModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['comment', 'profile']


class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    posts = models.ManyToManyField('Post', related_name='hashtags', blank=True)
    
    class Meta:
        indexes = [
            models.Index(
                fields=['name'], name='hash_tag_name_idx'
            )
        ]

    def __str__(self):
        return f"#{self.name}"


class PostView(BaseModel):
    viewer = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('viewer', 'post')
        indexes = [models.Index(fields=['post', 'viewed_at'])]
        ordering = ['-viewed_at']


class SavedPost(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    
    class Meta:
        unique_together = ('profile', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.profile} saved {self.post}"


class Mention(BaseModel):
    from_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mentions_made')
    to_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mentions_received')
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE)