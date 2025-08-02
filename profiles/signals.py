# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from profiles.models import Profile
from mentor.models import MentorProfile, MentorStatus

@receiver(post_save, sender=Profile)
def update_mentor_status_on_blacklist_change(sender, instance, **kwargs):
    try:
        mentor_profile = instance.mentor_profile
    except MentorProfile.DoesNotExist:
        return

    # Set to SUSPENDED if blacklisted
    if instance.mentor_blacklisted and mentor_profile.status != MentorStatus.SUSPENDED:
        mentor_profile.status = MentorStatus.SUSPENDED
        mentor_profile.save(update_fields=['status'])

    # Set to ACTIVE if not blacklisted
    elif not instance.mentor_blacklisted and mentor_profile.status == MentorStatus.SUSPENDED:
        mentor_profile.status = MentorStatus.ACTIVE
        mentor_profile.save(update_fields=['status'])