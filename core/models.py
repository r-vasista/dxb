
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from ckeditor.fields import RichTextField

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


class EmailTemplate(BaseModel):
    """Model to store email template configurations"""
    name = models.CharField(max_length=100, unique=True)
    subject = RichTextField()
    title = RichTextField()
    main_content = RichTextField()
    footer_content = RichTextField()
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'email_templates'


class EmailConfiguration(BaseModel):
    """Model to store fixed header and footer content"""
    header_content = models.TextField()
    footer_content = models.TextField()
    company_name = models.CharField(max_length=100)
    company_logo_url = models.URLField(blank=True, null=True)
    contact_email = models.EmailField()
    copy_right_notice = models.TextField()
    
    def __str__(self):
        return f"{self.company_name}"
    
    class Meta:
        db_table = 'email_configurations'
    