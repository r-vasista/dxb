# Django imports
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Local import
from core.models import BaseModel
from organization.models import (
    Organization
)
from profiles.choices import (
    VisibilityStatus, FieldType, ProfileType
)

User = get_user_model()


class Profile(BaseModel):
    """
    A profile linked to either a User (individual) or an Organization (org),
    never both.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='profile'
    )
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='profile'
    )
    username = models.CharField(max_length=200, unique=True, blank=True, null=True)

    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/profile_picture/', blank=True, null=True)
    cover_picture = models.ImageField(upload_to='profiles/cover_picture/', blank=True, null=True)
    profile_type = models.CharField(
        max_length=20,
        choices=ProfileType.choices
    )
    visibility_status = models.CharField(
        max_length=20,
        choices=VisibilityStatus.choices,
        default=VisibilityStatus.PUBLIC
    )
    friends = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True,
    )
    following = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True
    )

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()
    
    @property
    def friends_count(self):
        return self.friends.count()


    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    # One and only one of them must be set (XOR logic)
                    (models.Q(user__isnull=False) & models.Q(organization__isnull=True)) |
                    (models.Q(user__isnull=True) & models.Q(organization__isnull=False))
                ),
                name='only_one_profile_target',
            ),
            models.UniqueConstraint(
                fields=['user'], condition=models.Q(user__isnull=False),
                name='unique_user_profile'
            ),
            models.UniqueConstraint(
                fields=['organization'], condition=models.Q(organization__isnull=False),
                name='unique_organization_profile'
            ),
        ]

    def __str__(self):
        return f"Profile for {'User: ' + str(self.user) if self.user else 'Org: ' + str(self.organization)}"


class ProfileFieldSection(BaseModel):
    """
    Represents a group/section for organizing profile fields (like tabs or grouped fields).
    """
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='field_sections'
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        unique_together = ('profile', 'title')
        ordering = ['profile', 'display_order']

    def __str__(self):
        return f"{self.profile} - Section: {self.title}"



class ProfileField(BaseModel):
    """
    Stores dynamic fields for a Profile (either User or Organization).
    """
    profile = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='dynamic_fields'
    )
    section = models.ForeignKey(
        ProfileFieldSection,
        on_delete=models.CASCADE,
        related_name='fields',
        null=True,
        blank=True
    )

    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=FieldType.choices, default=FieldType.TEXT)

    text_value = models.TextField(blank=True, null=True)
    image_value = models.ImageField(upload_to='profile_fields/images/', blank=True, null=True)
    file_value = models.FileField(upload_to='profile_fields/files/', blank=True, null=True)
    date_value = models.DateField(blank=True, null=True)

    is_public = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['profile', 'field_name']),
            models.Index(fields=['profile', 'display_order']),
            models.Index(fields=['profile', 'is_public']),
            models.Index(fields=['field_type']),
            models.Index(fields=['text_value']),
            models.Index(fields=['date_value']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'field_name'],
                condition=models.Q(is_active=True),
                name='unique_profile_field_name'
            ),
        ]
        ordering = ['profile', 'display_order', 'field_name']

    def __str__(self):
        return f"{self.profile} - {self.field_name}"

    def get_value(self):
        if self.field_type == FieldType.TEXT:
            return self.text_value
        elif self.field_type == FieldType.IMAGE:
            return self.image_value
        elif self.field_type == FieldType.FILE:
            return self.file_value
        elif self.field_type == FieldType.DATE:
            return self.date_value
        return None

    def clean(self):
        super().clean()

        if self.field_type == FieldType.TEXT and not self.text_value:
            raise ValidationError(f"Text value is required for field '{self.field_name}'.")
        elif self.field_type == FieldType.DATE and not self.date_value:
            raise ValidationError(f"Date value is required for field '{self.field_name}'.")
        elif self.field_type == FieldType.IMAGE and not self.image_value:
            raise ValidationError(f"Image is required for field '{self.field_name}'.")
        elif self.field_type == FieldType.FILE and not self.file_value:
            raise ValidationError(f"File is required for field '{self.field_name}'.")

        value_counts = sum([
            1 if self.text_value else 0,
            1 if self.image_value else 0,
            1 if self.file_value else 0,
            1 if self.date_value else 0,
        ])
        if value_counts > 1:
            raise ValidationError("Only one value field should be set based on field_type.")

        if not self.field_name or not self.field_name.strip():
            raise ValidationError("Field name cannot be empty.")


class FriendRequest(BaseModel):
    """
    Friend request between two profiles: from -> to.
    """
    from_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests'
    )
    to_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='received_friend_requests'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    class Meta:
        unique_together = [('from_profile', 'to_profile')]
        indexes = [
            models.Index(fields=['from_profile', 'to_profile']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.from_profile} → {self.to_profile} [{self.status}]"
