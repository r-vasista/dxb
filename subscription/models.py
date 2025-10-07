from django.db import models
from core.models import (
    BaseModel
)
from profiles.models import (
    Profile
)


class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)

    # Optional feature flags for fast lookups
    unlimited_edits = models.BooleanField(default=False)
    invisible_delete = models.BooleanField(default=False)
    scheduled_posts = models.BooleanField(default=False)
    gold_ring = models.BooleanField(default=False)
    custom_chat_themes = models.BooleanField(default=False)
    creative_analytics = models.BooleanField(default=False)
    canvas_frames = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class UserSubscription(BaseModel):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_premium(self):
        return self.plan and self.plan.name.lower() != "free" and self.is_active

    def __str__(self):
        return f"{self.profile.username} - {self.plan.name}"


class ChatEditLimit(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    edit_count = models.PositiveIntegerField(default=0)
    delete_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('profile', 'date')
