# Django imports
from django.db import models

# Local imports
from core.models import (
    BaseModel
)
from mentor.choices import (
    MentorStatus
)
from profiles.models import (
    Profile
)

class MentorEligibilityCriteria(BaseModel):
    min_followers = models.IntegerField(default=500)  
    min_posts = models.IntegerField(default=45)
    post_streak_window_days = models.IntegerField(default=90)
    min_account_age_months = models.IntegerField(default=3)
    min_avg_engagement = models.FloatField(default=25.0)
    require_verified_profile = models.BooleanField(default=True)
    
    def __str__(self):
        return str(self.id)


class MentorMetrics(BaseModel):
    profile = models.OneToOneField(
        Profile,  # Replace with your actual Profile model path
        on_delete=models.CASCADE,
        related_name='mentor_eligibility'
    )
    
    # Eligibility criteria tracking
    followers_count = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)
    post_streak_window_days = models.IntegerField(default=90)
    min_account_age_months = models.PositiveIntegerField(default=0)
    avg_engagement_per_post = models.FloatField(default=0.0)
    avg_engagement = models.FloatField(default=25.0)
    
    def __str__(self):
        return self.profile.username

    
class MentorProfile(BaseModel):
    """
    Extended mentor profile information
    """
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='mentor_profile'
    )
    
    # Mentor specific fields
    specializations = models.TextField(help_text="Art styles/techniques mentor specializes in")
    experience_years = models.PositiveIntegerField(default=0)
    max_mentees = models.PositiveIntegerField(default=5)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status and availability
    status = models.CharField(
        max_length=20,
        choices=MentorStatus.choices,
        default=MentorStatus.ACTIVE
    )
    is_featured = models.BooleanField(default=False)
    is_accepting_requests = models.BooleanField(default=True)
    
    # Stats
    total_mentees = models.PositiveIntegerField(default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Mentor: {self.profile.username}"