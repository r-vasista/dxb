import uuid

# Django imports
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Local import
from core.models import (
    BaseModel, Country, City, State
)
from organization.models import (
    Organization
)
from profiles.choices import (
    VisibilityStatus, FieldType, ProfileType, StaticFieldType, DocumentType, VerificationStatus
)
from profiles.utils import (
    validate_username_format
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
    username = models.CharField(max_length=200, unique=True, blank=True, null=True, validators=[validate_username_format])
    phone_number = models.CharField(blank=True, null=True)

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
    view_count = models.PositiveIntegerField(default=0)

    tools=models.TextField( blank=True,null=True)
    awards=models.TextField(blank=True,null=True)

    city = models.ForeignKey(City, blank=True, null=True, on_delete=models.SET_NULL)
    state = models.ForeignKey(State, blank=True, null=True, on_delete=models.SET_NULL)
    country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.SET_NULL)

    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    notify_email = models.BooleanField(default=True)
    
    last_active_at = models.DateTimeField(null=True, blank=True)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    art_service_enabled = models.BooleanField(default=False)
    allow_mentions = models.BooleanField(default=True)
    
    mentor_eligibile = models.BooleanField(default=False)
    mentor_blacklisted = models.BooleanField(default=False)
    mentor_mail_sent = models.BooleanField(default=False)

    
    wall_tutorial = models.BooleanField(default=False)
    profile_tutorial = models.BooleanField(default=False)
    onboarding_required = models.BooleanField(default=True)
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_profiles'
    )
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )
    points = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        # Normalize username to lowercase before saving
        if self.username:
            self.username = self.username.lower()
            
        # Auto-generate referral code only when creating a new profile
        if not self.referral_code:
            code = str(uuid.uuid4()).split("-")[0].upper()
            # Ensure uniqueness
            while Profile.objects.filter(referral_code=code).exists():
                code = str(uuid.uuid4()).split("-")[0].upper()
            self.referral_code = code
            
        super().save(*args, **kwargs)
    
    def add_points(self, amount: int):
        self.points += amount
        self.save(update_fields=["points"])

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
        indexes = [
            models.Index(fields=['username'], name='profile_username_idx'),
            models.Index(fields=['bio'], name='profile_bio_idx'),
            models.Index(fields=['tools'], name='profile_tools_idx'),
            models.Index(fields=['awards'], name='profile_awards_idx'),
        ]

    def __str__(self):
        return f"{'User: ' + str(self.username), self.id if self.user else 'Org: ' + str(self.username), self.id}"


class ProfileCanvas(BaseModel):
    """
    Stores the canvas images of profile
    """
    profile = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='profile_canvas'
    )
    image = models.ImageField(upload_to='profiles/canvas_picture/', blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['profile'])
        ]
        ordering = ['display_order']
    
    def __str__(self):
        return f"{self.profile} {self.image}"


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
        constraints = [
            models.UniqueConstraint(
                fields=['from_profile', 'to_profile'],
                condition=models.Q(status='pending'),
                name='unique_pending_friend_request'
            )
        ]
        indexes = [
            models.Index(fields=['from_profile', 'to_profile']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.from_profile} → {self.to_profile} [{self.status}]"


class StaticProfileSection(BaseModel):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title}"


class StaticProfileField(BaseModel):
    section = models.ForeignKey(StaticProfileSection, related_name='fields', on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=10, choices=StaticFieldType.choices, default=StaticFieldType.TEXT)
    is_public = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.field_name}"


class StaticFieldValue(BaseModel):
    """
    Stores the actual value entered by a Profile for a global FieldTemplate.
    """
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='template_field_responses')
    static_field = models.ForeignKey(StaticProfileField, on_delete=models.CASCADE, related_name='responses')
    
    # Different value fields for different types
    text_value = models.TextField(blank=True, null=True)
    date_value = models.DateField(blank=True, null=True)
    image_value = models.ImageField(upload_to='static_fields/images/', blank=True, null=True)
    file_value = models.FileField(upload_to='static_fields/files/', blank=True, null=True)
    number_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    boolean_value = models.BooleanField(blank=True, null=True)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('profile', 'static_field') 
        indexes = [
            models.Index(fields=['profile', 'static_field']),
        ]

    def __str__(self):
        return f"{self.profile} - {self.static_field.field_name}"
    
    def get_value(self):
        """Get the value based on field type"""
        field_type = self.static_field.field_type
        
        if field_type == StaticFieldType.TEXT or field_type == StaticFieldType.TEXTAREA or field_type == StaticFieldType.EMAIL or field_type == StaticFieldType.URL:
            return self.text_value
        elif field_type == StaticFieldType.DATE:
            return self.date_value
        elif field_type == StaticFieldType.IMAGE:
            return self.image_value
        elif field_type == StaticFieldType.FILE:
            return self.file_value
        elif field_type == StaticFieldType.NUMBER:
            return self.number_value
        elif field_type == StaticFieldType.BOOLEAN:
            return self.boolean_value
        
        return None

    def set_value(self, value):
        """Set the value based on field type"""
        field_type = self.static_field.field_type
        
        # Clear all values first
        self.text_value = None
        self.date_value = None
        self.image_value = None
        self.file_value = None
        self.number_value = None
        self.boolean_value = None
        
        if field_type == StaticFieldType.TEXT or field_type == StaticFieldType.TEXTAREA or field_type == StaticFieldType.EMAIL or field_type == StaticFieldType.URL:
            self.text_value = value
        elif field_type == StaticFieldType.DATE:
            self.date_value = value
        elif field_type == StaticFieldType.IMAGE:
            self.image_value = value
        elif field_type == StaticFieldType.FILE:
            self.file_value = value
        elif field_type == StaticFieldType.NUMBER:
            self.number_value = value
        elif field_type == StaticFieldType.BOOLEAN:
            self.boolean_value = value


class ProfileView(BaseModel):
    viewer = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='views')
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('viewer', 'profile')
        indexes = [models.Index(fields=['profile', 'viewed_at'])]
        ordering = ['-viewed_at']


class ArtService(BaseModel):
    """Separate model to handle all art service related data"""
    profile = models.OneToOneField(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='art_service'
    )
    
    # Contact information
    service_phone = models.CharField(max_length=20, blank=True, null=True)
    service_email = models.EmailField(blank=True, null=True)
    
    # Service details
    description = models.TextField(blank=True, null=True)
    pricing = models.TextField(blank=True, null=True)
    specialties = models.TextField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    
    # Additional service fields - easily extensible
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    availability_hours = models.TextField(blank=True, null=True)
    min_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Service preferences
    accepts_rush_orders = models.BooleanField(default=False)
    offers_consultations = models.BooleanField(default=True)
    offers_revisions = models.BooleanField(default=True)
    max_revisions = models.PositiveIntegerField(blank=True, null=True)
    
    # Social proof
    client_testimonials = models.TextField(blank=True, null=True)
    certifications = models.TextField(blank=True, null=True)
    
    # Metrics
    total_projects_completed = models.PositiveIntegerField(default=0)
    response_time_hours = models.PositiveIntegerField(default=24)
    
    class Meta:
        verbose_name = "Art Service"
        verbose_name_plural = "Art Services"
    
    def __str__(self):
        return f"{self.profile.username}'s Art Service"
    
    @property
    def total_inquiries(self):
        """Get total number of inquiries"""
        return self.profile.art_service_inquiries.count()


class ArtServiceInquiry(models.Model):
    """Track when users inquire about an artist's contact info"""

    artist_profile = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='art_service_inquiries'
    )
    inquirer_profile = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='my_art_inquiries'
    )
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    artist_notified = models.BooleanField(default=False)

    class Meta:
        unique_together = ['artist_profile', 'inquirer_profile']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.inquirer_profile.username} -> {self.artist_profile.username}"
    

class VerificationRequest(BaseModel):
    """
    A verification request raised by a user.
    Admins approve/reject this request after reviewing linked documents.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="verification_requests"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        Profile, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_verification_requests"
    )
    rejection_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"VerificationRequest({self.profile.username}) - {self.status}"


class UserDocument(BaseModel):
    """
    Stores documents uploaded as part of a verification request.
    """

    request = models.ForeignKey(
        VerificationRequest, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=50, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    file = models.FileField(upload_to="user_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request.profile.username} - {self.document_type}"
    