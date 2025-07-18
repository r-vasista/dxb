from celery import shared_task
from django.core.management import call_command

@shared_task
def send_inactivity_reminders_via_command():
    # This runs your management command internally
    call_command('send_inactivity_reminders')
