from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Count, F
from django.db.models.functions import ExtractHour

from django.contrib.auth import get_user_model
from event.choices import AttendanceStatus, EventActivityType
from event.models import Event, EventActivityLog, EventAttendance, EventComment, EventMedia,EventStatus
from core.services import get_actual_user, send_dynamic_email_using_template
from notification.task_monitor import monitor_task
from profiles . models import Profile

from notification.models import NotificationType

from notification.utils import create_notification, send_notification_email

import logging


logger = logging.getLogger(__name__)


@shared_task
@monitor_task(task_name="mark_completed_events_and_notify", expected_interval_minutes=60)
def mark_completed_events_and_notify():
    logger.info("Running: mark_completed_events_and_notify")
    now = timezone.now()
    one_hour_ago = now - timezone.timedelta(hours=1)

    logger.info(f"[MarkCompletedEvents] Starting task at {now}. Checking events before {one_hour_ago}...")

    event_to_mark = Event.objects.filter(
        end_datetime__lte=one_hour_ago,
        status=EventStatus.PUBLISHED,
        completion_mail_sent=False 
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
        event.completion_mail_sent = True
        event.save(update_fields=['completion_mail_sent'])
    logger.info(f"[MarkCompletedEvents] Task completed. Total events marked: {completed_count}")


@shared_task
def send_event_analytics_report_task(event_id):
    try:
        event = Event.objects.get(id=event_id)

        reach = EventActivityLog.objects.filter(
            event=event,
            activity_type=EventActivityType.VIEW
        ).values('profile').distinct().count()

        attendance_stats = (
            EventAttendance.objects
            .filter(event=event)
            .values('status')
            .annotate(count=Count('id'))
        )
        rsvp_counts = {status: 0 for status in AttendanceStatus.values}
        for entry in attendance_stats:
            rsvp_counts[entry["status"]] = entry["count"]

        rsvped_users = EventAttendance.objects.filter(
            event=event
        ).values('profile').distinct().count()

        rsvp_rate = (rsvped_users / reach * 100) if reach > 0 else 0

        peak_hour = EventActivityLog.objects.filter(
            event=event,
            activity_type__in=[EventActivityType.VIEW, EventActivityType.COMMENT]
        ).annotate(hour=ExtractHour('timestamp')).values('hour').annotate(
            total=Count('id')
        ).order_by('-total').first()

        top_commenters = EventComment.objects.filter(
            event=event
        ).values('profile__username').annotate(
            total_comments=Count('id')
        ).order_by('-total_comments')[:5]

        context = {
            "event_title": event.title,
            "reach": reach,
            "rsvp_counts": rsvp_counts,
            "rsvp_rate": round(rsvp_rate, 2),
            "peak_engagement_hour": peak_hour["hour"] if peak_hour else None,
            "top_commenters": list(top_commenters),
        }

        def send_email_and_notify():
            try:
                all_profiles = [event.host] + list(event.co_hosts.all())
                for profile in all_profiles:
                    user = get_actual_user(profile)
                    if not user or not user.email:
                        continue

                    # Send email
                    send_dynamic_email_using_template(
                        template_name="event-analytics-report",
                        recipient_list=[user.email],
                        context={**context, "name": profile.username},
                    )

                    # Send in-app notification
                    create_notification(
                        sender=event.host,
                        recipient=profile,
                        instance=event,
                        message=f"Your weekly analytics report for event \"{event.title}\" is now available.",
                        notification_type=NotificationType.EVENT_REMINDER
                    )
            except Exception as e:
                logger.warning(f"[AnalyticsReport] Failed to send email or notify: {e}", exc_info=True)

        transaction.on_commit(send_email_and_notify)

    except Event.DoesNotExist:
        logger.warning(f"[AnalyticsReport] Event with ID {event_id} not found.")
    except Exception as e:
        logger.error(f"[AnalyticsReport] Unexpected error: {e}", exc_info=True)

@shared_task
@monitor_task(task_name="trigger_event_analytics_for_all_events", expected_interval_minutes=1440)
def trigger_event_analytics_for_all_events():
    logger.info("Running: trigger_event_analytics_for_all_events")
    """
    This task triggers analytics for all events by scheduling the send_event_analytics_report_task for each event.
    It runs daily to ensure all events are processed.
    """
    try:
        now = timezone.now()
        events = Event.objects.filter(
            status__in=[
                EventStatus.PUBLISHED,
                EventStatus.DRAFT,
                EventStatus.CANCELLED
            ]
        )

        for event in events:
            send_event_analytics_report_task.delay(event.id)

        return f"Triggered analytics for {events.count()} events."

    except Exception as e:
        logger.error(f"[AnalyticsTrigger] Failed to schedule analytics: {e}", exc_info=True)
        return "Error occurred"
    
