from django.contrib import admin
from subscription.models import (
    SubscriptionPlan, UserSubscription, ChatEditLimit
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'duration_days']
    search_fields = ['id', 'name', 'price', 'duration_days']
    list_filter = ['id', 'name', 'price', 'duration_days']
    

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'plan', 'start_date', 'end_date', 'is_active']
    search_fields = ['id', 'profile', 'plan', 'start_date', 'end_date', 'is_active']
    list_filter = ['id', 'profile', 'plan', 'start_date', 'end_date', 'is_active']


@admin.register(ChatEditLimit)
class ChatEditLimitAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'date', 'edit_count', 'delete_count']
    search_fields = ['id', 'profile', 'date', 'edit_count', 'delete_count']
    list_filter = ['id', 'profile', 'date', 'edit_count', 'delete_count']
