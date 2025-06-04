# Django imports
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, UniqueConstraint

# Local imports
from user.manager import CustomUserManager
from core.models import BaseModel, BaseTypeModel
from user.choices import PermissionType

class Permission(BaseModel):
    TYPE_CHOICES = [
        ('view', 'View'),
        ('create', 'Create'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
    ]
    
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='permissions')
    type = models.CharField(max_length=10, choices=PermissionType.choices)
    
    class Meta:
        unique_together = ['content_type', 'type']
    
    def __str__(self):
        return f"{self.content_type.app_label}.{self.code}"


class Role(BaseModel):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        'organization.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='roles'
    )
    permissions = models.ManyToManyField(Permission, blank=True)

    class Meta:
        constraints = [
            # Unique name when organization is NULL (global roles)
            UniqueConstraint(
                fields=['name'],
                condition=Q(organization__isnull=True),
                name='unique_global_role_name'
            ),
            # Unique name per organization when organization is set
            UniqueConstraint(
                fields=['name', 'organization'],
                condition=Q(organization__isnull=False),
                name='unique_org_role_name'
            )
        ]

    def __str__(self):
        if self.organization:
            return f"{self.name} ({self.organization.name})"
        return self.name


class UserType(BaseTypeModel):
    class Meta:
        verbose_name = "User Type"
        verbose_name_plural = "User Types"
    

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    user_type = models.ForeignKey(UserType, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)

    roles = models.ManyToManyField(Role, related_name='custom_users')
    custom_permissions = models.ManyToManyField(Permission, blank=True, related_name='custom_users')

    objects = CustomUserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.user_type.code})"
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.email