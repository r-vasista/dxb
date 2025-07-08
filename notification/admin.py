from django.contrib import admin
from notification.models import (
    Notification
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'sender', 'notification_type', 'object_id']
    search_fields = ['id', 'recipient', 'sender', 'notification_type', 'object_id']
    list_filter = ['id', 'recipient', 'sender', 'notification_type', 'object_id']