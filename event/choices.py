from django.db import models


class EventType(models.TextChoices):
    WORKSHOP = 'workshop', 'Workshop'
    SEMINAR = 'seminar', 'Seminar'
    CONFERENCE = 'conference', 'Conference'
    MEETUP = 'meetup', 'Meetup'
    WEBINAR = 'webinar', 'Webinar'
    SOCIAL = 'social', 'Social Event'
    NETWORKING = 'networking', 'Networking'
    OTHER = 'other', 'Other'


class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class AttendanceStatus(models.TextChoices):
    INTERESTED = 'interested', 'Interested'
    NOT_INTERESTED = 'not_interested', 'Not Interested'
    PENDING = 'pending', 'Pending'
    DECLINED = 'declined', 'Declined'
    