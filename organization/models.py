# Django imports
from django.db import models
from django.utils.text import slugify

# Local import
from core.models import BaseModel, BaseTypeModel
from user.models import CustomUser
from organization.choices import OrganizationStatus, VisibilityStatus

# External imports
from phonenumber_field.modelfields import PhoneNumberField



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
    user = models.OneToOneField(CustomUser, on_delete=models.PROTECT, related_name='organization')
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField()
    website = models.URLField(blank=True, null=True)
    
    organization_type = models.ForeignKey(OrganizationType, on_delete=models.PROTECT)
    industry_type = models.ForeignKey(IndustryType, on_delete=models.PROTECT)
    
    description = models.TextField(blank=True, null=True)
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