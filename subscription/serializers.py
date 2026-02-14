from rest_framework import serializers
from .models import SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "name", "description", "price", "currency", "duration_days",
            "unlimited_edits", "invisible_delete", "scheduled_posts",
            "gold_ring", "custom_chat_themes", "creative_analytics", "canvas_frames"
        ]
