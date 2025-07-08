from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from notification.models import (
    Notification,DailyQuote
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
