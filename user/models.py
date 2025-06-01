# Django imports
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType

# Local imports
from user.manager import CustomUserManager
from core.models import BaseModel, BaseTypeModel
from user.choices import PermissionType

class Permission(models.Model):
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


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
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