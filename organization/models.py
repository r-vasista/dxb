# Django imports
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Local import
from core.models import BaseModel, BaseTypeModel
from organization.choices import (
    OrganizationStatus, VisibilityStatus, FieldType, OrgInviteStatus
)

# External imports
from phonenumber_field.modelfields import PhoneNumberField

# Python imports
import uuid


User = get_user_model()


class Address(BaseModel):
    """
    Model to store address information.
    """
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['state']),
            models.Index(fields=['country']),
            models.Index(fields=['postal_code']),
        ]

    def __str__(self):
        return f'{self.address}, {self.city}, {self.state} {self.postal_code}'
    

class OrganizationType(BaseTypeModel):
    class Meta:
        verbose_name = "Organization Type"
        verbose_name_plural = "Organization Types"

class IndustryType(BaseTypeModel):
    class Meta:
        verbose_name = "Industry Type"
        verbose_name_plural = "Industry Types"
    

class Organization(BaseModel):
    """
    Model representing an organization/company.
    """
    name = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='organization')
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField()
    website = models.URLField(blank=True, null=True)
    
    organization_type = models.ForeignKey(OrganizationType, on_delete=models.PROTECT)
    industry_type = models.ForeignKey(IndustryType, on_delete=models.PROTECT)
    
    description = models.TextField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='organizations/logos/', blank=True, null=True)
    
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        related_name='organization',
        null=True,
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.PENDING
    )

    visibility_status = models.CharField(
        max_length=20,
        choices = VisibilityStatus.choices,
        default = VisibilityStatus.PUBLIC
    )

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['organization_type']),
            models.Index(fields=['industry_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_active=True),
                name='unique_active_organization_name'
            ),
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(is_active=True),
                name='unique_active_organization_email'
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """Generate a unique slug for the organization."""
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1
        
        while Organization.objects.filter(slug=slug, is_active=True).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        
        return slug


class OrganizationProfileField(BaseModel):
    """
    Single table to store all organization profile fields with their values.
    Each organization can add any number of custom fields.
    """
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='profile_fields'
    )
    
    # Field definition
    field_name = models.CharField(
        max_length=100,
        help_text="Name of the field (e.g., 'Website URL', 'Founded Year', 'Contact Email')"
    )
    field_type = models.CharField(
        max_length=10,
        choices=FieldType.choices,
        default=FieldType.TEXT,
        help_text="Type of field determines which value field to use"
    )
    
    # Value storage - only one will be used based on field_type
    text_value = models.TextField(
        blank=True, 
        null=True,
        help_text="For TEXT type - stores URLs, emails, phone numbers, descriptions, etc."
    )
    image_value = models.ImageField(
        upload_to='organization_profiles/images/', 
        blank=True, 
        null=True,
        help_text="For IMAGE type fields"
    )
    file_value = models.FileField(
        upload_to='organization_profiles/files/', 
        blank=True, 
        null=True,
        help_text="For FILE type fields"
    )
    date_value = models.DateField(
        blank=True, 
        null=True,
        help_text="For DATE type fields"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Should this field be visible on public profile?"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which field appears on profile"
    )
    
    # Optional metadata
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Additional description or notes about this field"
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null= True)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'field_name']),
            models.Index(fields=['organization', 'display_order']),
            models.Index(fields=['organization', 'is_public']),
            models.Index(fields=['field_type']),
            models.Index(fields=['text_value']),  # For searching text content
            models.Index(fields=['date_value']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'field_name'],
                condition=models.Q(is_active=True),
                name='unique_org_field_name'
            ),
        ]
        ordering = ['organization', 'display_order', 'field_name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.field_name}"
    
    def get_value(self):
        """
        Return the appropriate value based on field type.
        """
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
        """
        Validate the profile field and its value.
        """
        super().clean()
        
        # Check that the appropriate value field is set based on field_type
        if self.field_type == FieldType.TEXT and not self.text_value:
                raise ValidationError(f"Text value is required for field '{self.field_name}'.")
        
        elif self.field_type == FieldType.DATE and not self.date_value:
                raise ValidationError(f"Date value is required for field '{self.field_name}'.")
        
        elif self.field_type == FieldType.IMAGE and not self.image_value:
                raise ValidationError(f"Image is required for field '{self.field_name}'.")
        
        elif self.field_type == FieldType.FILE and not self.file_value:
                raise ValidationError(f"File is required for field '{self.field_name}'.")
        
        # Ensure only the correct value field is set
        value_counts = sum([
            1 if self.text_value else 0,
            1 if self.image_value else 0,
            1 if self.file_value else 0,
            1 if self.date_value else 0,
        ])
        
        if value_counts > 1:
            raise ValidationError("Only one value field should be set based on field_type.")
        
        # Validate field_name is not empty
        if not self.field_name or not self.field_name.strip():
            raise ValidationError("Field name cannot be empty.")


class Position(BaseModel):
    """
    Job positions/roles within the organization
    """
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='user_positions')
    
    class Meta:
        unique_together = ['organization', 'code']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.organization.name}"


class OrganizationInvite(BaseModel):
    """
    Invite system for organization members
    """
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='invites')
    
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=OrgInviteStatus.choices, default=OrgInviteStatus.PENDING)
    expires_at = models.DateTimeField()
    
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    message = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['organization', 'email', 'status']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Invite: {self.email} to {self.organization.name}"
    

class OrganizationMember(BaseModel):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name='organization_memebers')

    class Meta:
        unique_together = ['organization', 'user']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.organization.name} )"
