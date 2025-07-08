# Django imports
from django.db import models
from django.utils import timezone

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

# Python imports
import pytz


class Event(models.Model):
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
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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


class EventAttendance(models.Model):
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
    registered_at = models.DateTimeField(auto_now_add=True)
    checked_in = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['profile', 'event']
        
    def __str__(self):
        return f"{self.profile.username} - {self.event.title} ({self.status})"
