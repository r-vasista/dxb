# app/utils/task_monitor.py
import logging
from time import perf_counter
from functools import wraps
from django.utils import timezone
from django.contrib.auth import get_user_model
from profiles.models import Profile  # adjust import path if needed
from .models import ScheduledTaskMonitor
from notification.utils import create_notification, send_notification_email

logger = logging.getLogger(__name__)
User = get_user_model()

def monitor_task(task_name, expected_interval_minutes):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = perf_counter()
            run_at = timezone.now()

            try:
                result = func(*args, **kwargs)
                duration = perf_counter() - start_time

                ScheduledTaskMonitor.objects.update_or_create(
                    task_name=task_name,
                    defaults={
                        "last_run_at": run_at,
                        "expected_interval_minutes": expected_interval_minutes,
                        "last_response": {
                            "success": True,
                            "error": None,
                            "duration_seconds": duration,
                            "result": str(result),
                            "run_at": run_at.isoformat(),
                        }
                    }
                )

                logger.info(f"Task '{task_name}' completed successfully at {run_at}")
                return result

            except Exception as e:
                logger.error(f" Task '{task_name}' failed: {str(e)}", exc_info=True)

                # Get all profiles whose linked user is a superuser
 
                superuser_profiles = Profile.objects.filter(user__is_superuser=True)
                print(f"Superuser profiles: {superuser_profiles}")

                msg = f"CRON job '{task_name}' failed: {str(e)}"

                for profile in superuser_profiles:
                    # In-app notification
                    create_notification(
                        sender=profile,
                        recipient=profile,
                        instance=None,
                        message=msg,
                        notification_type="CRON_FAILURE"
                    )

                    # Email notification
                    send_notification_email(
                        recipient=profile,
                        sender=profile,
                        message=msg,
                        notification_type="CRON_FAILURE"
                    )
                ScheduledTaskMonitor.objects.update_or_create(
                    task_name=task_name,
                    defaults={
                        "last_run_at": run_at,
                        "expected_interval_minutes": expected_interval_minutes,
                        "last_response": {
                            "success": False,
                            "error": str(e),
                            "duration_seconds": duration,
                            "result": None,
                            "run_at": run_at.isoformat(),
                        }
                    }
                )
                raise
        return wrapper
    return decorator
