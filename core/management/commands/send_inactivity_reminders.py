from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from profiles.models import Profile  
from django.core.mail import send_mail
from core.utils import get_inactivity_email_context, get_user
from core.services import send_dynamic_email_using_template


class Command(BaseCommand):
    help = 'Send reminder emails to inactive users'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        cutoff = now - timedelta(hours=48)
        eligible_profiles = Profile.objects.filter(
            notify_email=True,
        ).filter(
            Q(last_active_at__lt=cutoff) | Q(last_active_at__isnull=True)
        ).exclude(
            last_reminder_sent_at__gte=cutoff
        )

        for profile in eligible_profiles:
            # suggestions = get_suggested_content(profile)
            context = get_inactivity_email_context(profile)
            email_to = get_user(profile).email
            success, msg = send_dynamic_email_using_template(
                template_name="inactivity-reminder",
                recipient_list=[email_to],
                context=context,
            )
            self.stdout.write(self.style.SUCCESS(f"email to {email_to} was {success} {msg}"))
            if success:
                profile.last_reminder_sent_at = now
                profile.save(update_fields=['last_reminder_sent_at'])

        self.stdout.write(self.style.SUCCESS(f"Sent {eligible_profiles.count()} reminders"))
