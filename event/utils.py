from urllib.parse import urlencode
from django.utils.timezone import is_aware
import pytz 

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