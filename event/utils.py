from urllib.parse import urlencode
from django.utils.timezone import is_aware
from event.models import EventTag, Event
from django.shortcuts import get_object_or_404

import pytz 
import re

def generate_google_calendar_link(event, request=None):
    """
    Generates a Google Calendar add-event link using user's timezone.
    """
    # Determine user's timezone
    user_tz_str = getattr(request.user, 'timezone', 'UTC') if request and hasattr(request, 'user') else 'UTC'
    try:
        user_tz = pytz.timezone(user_tz_str)
    except pytz.UnknownTimeZoneError:
        user_tz = pytz.UTC

    # Convert UTC event times to user's local timezone
    start_local = event.start_datetime.astimezone(user_tz)
    end_local = event.end_datetime.astimezone(user_tz)

    # Google Calendar expects format YYYYMMDDTHHMMSS (no timezone indicator)
    def format_dt(dt):
        if not is_aware(dt):
            raise ValueError("Datetime must be timezone-aware")
        return dt.strftime("%Y%m%dT%H%M%S")

    params = {
        'action': 'TEMPLATE',
        'text': event.title,
        'dates': f"{format_dt(start_local)}/{format_dt(end_local)}",
        'details': event.description or '',
        'location': event.address or 'Online',
    }
    return f"https://www.google.com/calendar/render?{urlencode(params)}"

def extract_hashtags(text):
    """Extracts hashtags from a string (ignores case)."""
    return set(re.findall(r"#(\w+)", text or ""))

def handle_event_hashtags(event):
    """Extract hashtags from event fields and update M2M relation."""
    hashtag_text = f"{event.title or ''} {event.description or ''}"
    hashtags = extract_hashtags(hashtag_text)

    # Clear old hashtags
    event.tags.clear()

    for tag in hashtags:
        hashtag_obj, _ = EventTag.objects.get_or_create(name=tag.lower())
        event.tags.add(hashtag_obj)

def is_host_or_cohost(event, profile):
    """
    Returns True if the given profile is either the host or a co-host of the event.
    """
    if not event or not profile:
        return False

    # Check if profile is the main host
    if event.host_id == profile.id:
        return True

    # Check if profile is in the co-hosts ManyToMany relation
    return event.co_hosts.filter(id=profile.id).exists()

def get_event_by_id_or_slug(id=None, slug=None):
    if id:
        event = get_object_or_404(Event, id=id)
    elif slug:
        event = get_object_or_404(Event, slug=slug)
    else:
        raise ValueError('Event id or slug must be provided')
    return event