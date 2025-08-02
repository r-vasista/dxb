from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dxb.settings')

app = Celery('dxb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.enable_utc = False
app.conf.timezone = 'Asia/Kolkata'
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'send-daily-muse-to-all-profiles-every-minute': {
        'task': 'notification.task.send_daily_muse_to_all_profiles',
        'schedule': crontab(hour=16, minute=50),  # 🔁 Every day at 4:50 PM
    },
    'send-inactivity-reminders-every-6-hours': {
        'task': 'core.tasks.send_inactivity_reminders_via_command',
        'schedule': crontab(minute=0, hour='*/6'),  # 🔁 Every 6 hours at :00 (e.g., 12:00, 6:00, 18:00)
    },
    'send-weekly-profile-stats-every-minute': {
        'task': 'notification.task.send_weekly_profile_stats',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Every week at 8:00 AM on Monday
    },
    'send-event-reminder-notifications': {
        'task': 'notification.task.send_event_reminder_notifications',
        'schedule': crontab(minute=30), # Runs every 30 minutes
    },
    'notify-low-rsvp-events-every-3-hour': {
        'task': 'notification.task.notify_low_rsvp_events',
        'schedule': crontab(minute=0, hour='*/3'),  # Runs every 3 hour
    },
    'mark-completed-events-and-notify-every-1-hour': {
        'task': 'event.tasks.mark_completed_events_and_notify',
        'schedule': crontab(minute=0), #Runs every 1 hour
    },
    'trigger_event_analytics_for_all_events':{
        'task':'event.tasks.trigger_event_analytics_for_all_events',
        'schedule' : crontab(minute=0),    #Runs for every one hour
    },
    'run_mentor_eligibility_check': {
        'task': 'mentor.tasks.run_mentor_eligibility_check',
        'schedule': crontab(hour=3, minute=30),  # Every day at 3 AM (hour=3, minute=0),
    },
    
}