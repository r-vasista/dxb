from django.contrib import admin
from event.models import (
    Event
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'title', 'start_datetime']
    search_fields = ['id', 'profile', 'title', 'start_datetime']
    list_filter = ['id', 'profile', 'title', 'start_datetime']
