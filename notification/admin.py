from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from notification.models import (
    Notification,DailyQuote,DailyQuoteSeen, ScheduledTaskMonitor
)
from .resources import DailyQuoteResource

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'sender', 'notification_type', 'object_id']
    search_fields = ['id', 'recipient', 'sender', 'notification_type', 'object_id']
    list_filter = ['id', 'recipient', 'sender', 'notification_type', 'object_id']

@admin.register(DailyQuote)
class DailyQuoteAdmin(ImportExportModelAdmin):
    resource_class = DailyQuoteResource
    list_display = ['text', 'author']

@admin.register(DailyQuoteSeen)
class DailyQuoteSeenAdmin(admin.ModelAdmin):
    list_display=['profile','quote','email_sent']

@admin.register(ScheduledTaskMonitor)
class ScheduledTaskMonitorAdmin(admin.ModelAdmin):
    list_display=['task_name', 'last_run_at', 'expected_interval_minutes']