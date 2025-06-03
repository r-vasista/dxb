
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    inactivated_at = models.DateTimeField(null=True, blank=True)

    def deactivate(self):
        self.is_active = False
        self.inactivated_at = timezone.now()
        self.save()

    def activate(self):
        self.is_active = True
        self.inactivated_at = None
        self.save()

    class Meta:
        abstract = True


class BaseTypeModel(BaseModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.code:
            self.code = slugify(self.code)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
