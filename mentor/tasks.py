# Django imports
from django.db.models import Sum, Count, Q
from django.utils.timezone import now
from django.utils import timezone

# Python imports
from dateutil.relativedelta import relativedelta
from datetime import timedelta

# Third party imports
from celery import shared_task

# Local imports
from mentor.models import (
    MentorEligibilityCriteria, MentorMetrics
)
from profiles.models import (
    Profile
)
from profiles.choices import (
    ProfileType
)
from post.models import (
    Post
)
from post.choices import (
    PostStatus
)


def calculate_mentor_metrics_for_profile(profile):
    try:
        criteria = MentorEligibilityCriteria.objects.filter(is_active=True).first()
        if not criteria:
            print("No eligibility criteria found.")
            return
        account_age = relativedelta(now(), profile.created_at)
        account_age_months = account_age.years * 12 + account_age.months

        # Followers count
        followers_count = profile.followers.count()

        # Time window for post streak
        post_window_start = now() - timedelta(days=criteria.post_streak_window_days)

        # Posts in streak window
        posts = Post.objects.filter(profile=profile, created_at__gte=post_window_start)

        post_count = posts.count()

        total_engagement = posts.aggregate(
            total=Sum('reaction_count') + Sum('comment_count') + Sum('share_count')
        )['total'] or 0

        avg_engagement = total_engagement / post_count if post_count > 0 else 0.0

        # Check eligibility
        is_eligible = (
            followers_count >= criteria.min_followers and
            post_count >= criteria.min_posts and
            account_age_months >= criteria.min_account_age_months and
            avg_engagement >= criteria.min_avg_engagement and
            (not criteria.require_verified_profile or profile.is_verified)
        )

        # Update mentor_eligibile flag
        profile.mentor_eligibile = is_eligible
        profile.save(update_fields=['mentor_eligibile'])
        print('USER:', profile.username, '    ',  'ELIGIBLE:', is_eligible)

        # Update or create mentor metrics
        MentorMetrics.objects.update_or_create(
            profile=profile,
            defaults={
                'followers_count': followers_count,
                'posts_count': post_count,
                'post_streak_window_days': criteria.post_streak_window_days,
                'min_account_age_months': account_age_months,
                'avg_engagement': avg_engagement,
                'updated_at': timezone.now()
            }
        )

    except Exception as e:
        # Optional: log error
        print(f"[MentorMetricError] for profile {profile.id}: {e}")

@shared_task
def run_mentor_eligibility_check():
    profiles = Profile.objects.filter(is_active=True, mentor_blacklisted=False)

    for profile in profiles:
        calculate_mentor_metrics_for_profile(profile)


# from mentor.tasks import calculate_mentor_metrics_for_profile
# from profiles.models import Profile
# profile=Profile.objects.get(id=1)
# calculate_mentor_metrics_for_profile(profile)