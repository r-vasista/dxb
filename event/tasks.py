from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth import get_user_model
from event.models import Event, EventAttendance, EventComment, EventMedia,EventStatus
from core.services import get_actual_user
from profiles . models import Profile

from notification.models import NotificationType

from notification.utils import create_notification, send_notification_email

import logging


logger = logging.getLogger(__name__)


@shared_task
def mark_completed_events_and_notify():
    now = timezone.now()
    one_hour_ago = now - timezone.timedelta(hours=1)

    logger.info(f"[MarkCompletedEvents] Starting task at {now}. Checking events before {one_hour_ago}...")

    event_to_mark = Event.objects.filter(
        end_datetime__lte=one_hour_ago,
        status=EventStatus.PUBLISHED
    )

    completed_count = 0

    for event in event_to_mark:
        event.status = EventStatus.COMPLETED
        event.save()
        completed_count += 1

        logger.info(f"[MarkCompletedEvents] Event '{event.title}' (ID: {event.id}) marked as COMPLETED.")

        host = event.host
        host_user = get_actual_user(host)

        message = f"Your event '{event.title}' has been automatically marked as completed."
        create_notification(
            sender=host,
            recipient=host,
            instance=event,
            message=message,
            notification_type=NotificationType.STATUS_CHANGE
        )
        logger.info(f"[MarkCompletedEvents] Notified host: {host.username}")

        attendees = event.attendees.all()
        for attendee in attendees:
            attendee_user = get_actual_user(attendee)
            if attendee_user and attendee_user != host_user:
                message_attendee = f"The event '{event.title}' you attended is now marked as completed."
                create_notification(
                    sender=host,
                    recipient=attendee,
                    instance=event,
                    message=message_attendee,
                    notification_type=NotificationType.STATUS_CHANGE
                )
                logger.info(f"[MarkCompletedEvents] Notified attendee: {attendee.username}")

    logger.info(f"[MarkCompletedEvents] Task completed. Total events marked: {completed_count}")
