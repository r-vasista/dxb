from django.contrib import admin
from event.models import (
    Event
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'co_host', 'title', 'start_datetime']
    search_fields = ['id', 'host', 'co_host', 'title', 'start_datetime']
    list_filter = ['id', 'host', 'co_host', 'title', 'start_datetime']
