# Django imports
from django.contrib.auth.models import BaseUserManager

# Local imports

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if 'user_type' not in extra_fields:
            from user.models import UserType
            admin_type, _ = UserType.objects.get_or_create(
                code='admin',
                defaults={'name':'Admin'}
                )
            extra_fields['user_type'] = admin_type

        return self.create_user(email, password, **extra_fields)