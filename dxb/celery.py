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
        'schedule': crontab(hour=11, minute=0),  # 🔁 Every day at 11:00 AM
    },
}