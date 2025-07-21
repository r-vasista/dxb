# Django imports
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator

# Local imports
from event.choices import (
    EventType, EventStatus, AttendanceStatus
)
from profiles.models import (
    Profile
)
from core.models import (
    Country, City, State
)
from core.models import (
    BaseModel
)

# Python imports
import pytz

class EventTag(BaseModel):
    """
    Tags for categorizing events
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Event(BaseModel):
    """
    Events that can be created by profiles (users or organizations)
    """
    # Event organizer (the profile that created the event)
    host = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='organized_events'
    )
    co_host = models.ForeignKey(
        Profile, 
        on_delete=models.CASCADE, 
        related_name='co_host_organized_events',
        blank=True,
        null= True
    )
    
    # Basic event information
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.OTHER
    )
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PUBLISHED
    )
    
    # Date and time
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in pytz.all_timezones], default='UTC')
    
    # Location
    is_online = models.BooleanField(default=False)
    address = models.TextField(blank=True, null=True)
    city = models.ForeignKey(City, blank=True, null=True, on_delete=models.SET_NULL)
    state = models.ForeignKey(State, blank=True, null=True, on_delete=models.SET_NULL)
    country = models.ForeignKey(Country, blank=True, null=True, on_delete=models.SET_NULL)
    online_link = models.URLField(blank=True, null=True)
    
    # Event details
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Media
    event_image = models.ImageField(upload_to='events/images/', blank=True, null=True)
    
    # Attendees
    attendees = models.ManyToManyField(
        Profile,
        through='EventAttendance',
        related_name='attended_events',
        blank=True
    )
    
    class Meta:
        ordering = ['-start_datetime']
        
    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_past(self):
        return self.end_datetime < timezone.now()
    
    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()
    
    @property
    def attendee_count(self):
        return self.attendees.count()
    
    @property
    def spots_remaining(self):
        if self.max_attendees:
            return max(0, self.max_attendees - self.attendee_count)
        return None


class EventAttendance(BaseModel):
    """
    Through model for event attendance with additional fields
    """
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.INTERESTED
    )
    
    class Meta:
        unique_together = ['profile', 'event']
        
    def __str__(self):
        return f"{self.profile.username} - {self.event.title} ({self.status})"


class EventMedia(BaseModel):
    """
    Media files uploaded for events (images, videos, documents)
    """
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('audio', 'Audio'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='media')
    uploaded_by = models.ForeignKey(Profile, on_delete=models.CASCADE)
    
    # File fields
    file = models.FileField(
        upload_to='events/media/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov', 
                                 'pdf', 'doc', 'docx', 'mp3', 'wav']
            )
        ]
    )
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    
    # Media details
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    is_pinned = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.title or self.file.name} - {self.event.title}"
    
    def save(self, *args, **kwargs):
        # Auto-detect media type based on file extension
        if self.file:
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                self.media_type = 'image'
            elif ext in ['mp4', 'avi', 'mov']:
                self.media_type = 'video'
            elif ext in ['pdf', 'doc', 'docx']:
                self.media_type = 'document'
            elif ext in ['mp3', 'wav']:
                self.media_type = 'audio'
            
            # Set file size
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)


class EventComment(BaseModel):
    """
    Comments on events
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='comments')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    
    # Comment content
    content = models.TextField()

    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.profile.username} on {self.event.title}"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def reply_count(self):
        return self.replies.filter(is_active=True).count()
    

class EventCommentLike(BaseModel):
    """
    Likes on event comments
    """
    comment = models.ForeignKey(EventComment, on_delete=models.CASCADE, related_name='likes')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['comment', 'profile']
        
    def __str__(self):
        return f"{self.profile.username} likes comment on {self.comment.event.title}"


class EventMediaComment(BaseModel):
    """
    Comments on events
    """
    event_media = models.ForeignKey(EventMedia, on_delete=models.CASCADE, related_name='comments')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    
    # Comment content
    content = models.TextField()

    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.profile.username} on {self.event_media.event.title}"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    @property
    def reply_count(self):
        return self.replies.filter(is_active=True).count()
