from django.db import models

class MentorStatus(models.TextChoices):
    INACTIVE = 'inactive', 'Inactive'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    SUSPENDED = 'suspended', 'Suspended'