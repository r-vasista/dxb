from django.contrib import admin
from event.models import (
    Event, EventAttendance, EventComment, EventCommentLike, EventMedia, EventMediaComment, EventTag
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'title', 'start_datetime']
    search_fields = ['id', 'host', 'title', 'start_datetime']
    list_filter = ['id', 'host', 'title', 'start_datetime']


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'event', 'status', 'created_at']
    search_fields = ['id', 'profile', 'event', 'status', 'created_at']
    list_filter = ['id', 'profile', 'event', 'status', 'created_at']
    
    
@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ['id','event', 'uploaded_by', 'file', 'media_type']
    search_fields = ['id','event', 'uploaded_by', 'file', 'media_type']
    list_filter = ['id','event', 'uploaded_by', 'file', 'media_type']
    
@admin.register(EventMediaComment)
class EventMediaCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'event_media', 'parent', 'created_at']
    search_fields = ['id', 'profile', 'event_media', 'parent', 'created_at']
    list_filter = ['id', 'profile', 'event_media', 'parent', 'created_at']
    

@admin.register(EventTag)
class EventTagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    search_fields = ['id', 'name', 'created_at']
    list_filter = ['id', 'name', 'created_at']
