from django.contrib import admin

#Local imports
from mentor.models import (
    MentorEligibilityCriteria, MentorMetrics, MentorProfile
)


@admin.register(MentorEligibilityCriteria)
class MentorEligibilityCriteriaAdmin(admin.ModelAdmin):
    list_display = ['id', 'min_followers', 'min_posts', 'post_streak_window_days', 'min_avg_engagement', 'min_account_age_months']
    search_fields = ['id', 'min_followers', 'min_posts', 'post_streak_window_days', 'min_avg_engagement', 'min_account_age_months']
    list_filter = ['id', 'min_followers', 'min_posts', 'post_streak_window_days', 'min_avg_engagement', 'min_account_age_months']
  
    
@admin.register(MentorMetrics)
class MentorMetricsAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile']
    search_fields =  ['id', 'profile']
    list_filter = ['id', 'profile']


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'status']
    search_fields =  ['id', 'profile', 'status']
    list_filter = ['id', 'profile', 'status']



