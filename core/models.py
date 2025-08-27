
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from core.choices import ReportReason

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
    subject = models.TextField()
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


class WeeklyChallenge(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    hashtag = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    banner_image = models.ImageField(upload_to="weekly_challenges/banners/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    @property
    def is_current(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


class UpcomingFeature(BaseModel):
    title = models.CharField(max_length=255)
    description = RichTextField()
    status = models.BooleanField(default=True)  

    def __str__(self):
        return self.title

class FeatureStep(models.Model):
    feature = models.ForeignKey(UpcomingFeature, on_delete=models.CASCADE, related_name='steps')
    image = models.ImageField(upload_to='feature_steps/', blank=True, null=True)
    title = models.CharField(max_length=255)
    description = RichTextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']    
        unique_together = ('feature', 'order')

    def __str__(self):
        return f"{self.feature.title} - Step {self.order}: {self.title}"
    

class HashTag(models.Model):
    name = models.CharField(max_length=255, unique=True)
    

class Report(BaseModel):
    from profiles.models import Profile
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    reporter = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="reports_filed",
    )
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    details = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["reporter", "created_at"]),
            models.Index(fields=["reason"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "reporter", "reason"],
                name="one_report_per_reason_per_target_per_reporter",
            ),
        ]

    def __str__(self):
        return f"Report({self.id}) → {self.content_type.model}#{self.object_id}"
