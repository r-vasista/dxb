
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
    

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True, blank=True, null=True)  # ISO country code
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Countries"

class State(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, null=True)  # State code if applicable
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    
    def __str__(self):
        return f"{self.name}, {self.country.name}"
    
    class Meta:
        unique_together = ['name', 'country']

class City(models.Model):
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities', null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='cities')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    def __str__(self):
        if self.state:
            return f"{self.name}, {self.state.name}, {self.country.name}"
        return f"{self.name}, {self.country.name}"
    
    class Meta:
        verbose_name_plural = "Cities"
        unique_together = ['name', 'state', 'country']
