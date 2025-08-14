from celery import shared_task
from django.core.management import call_command
import logging
from notification.task_monitor import monitor_task
logger = logging.getLogger(__name__)

@shared_task
@monitor_task(task_name="send_inactivity_reminders_via_command", expected_interval_minutes=360) 
def send_inactivity_reminders_via_command():
    logger.info("Running: send_inactivity_reminders_via_command")
    # This runs your management command internally
    call_command('send_inactivity_reminders')
