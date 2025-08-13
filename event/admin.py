from django.contrib import admin
from event.models import (
    Event, EventAttendance, EventComment, EventCommentLike, EventMedia, EventMediaComment, EventTag, EventMediaLike, EventActivityLog
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'title', 'group', 'allow_public_media', 'start_datetime']
    search_fields = ['id', 'host', 'title', 'group', 'allow_public_media', 'start_datetime']
    list_filter = ['id', 'host', 'title', 'group', 'allow_public_media', 'start_datetime']


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'event', 'status', 'created_at']
    search_fields = ['id', 'profile', 'event', 'status', 'created_at']
    list_filter = ['id', 'profile', 'event', 'status', 'created_at']
    
    
@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ['id','event', 'uploaded_by', 'file', 'media_type', 'uploaded_by_host']
    search_fields = ['id','event', 'uploaded_by', 'file', 'media_type', 'uploaded_by_host']
    list_filter = ['id','event', 'uploaded_by', 'file', 'media_type', 'uploaded_by_host']
    
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

@admin.register(EventMediaLike)
class EventMediaLikeAdmin(admin.ModelAdmin):
    list_display = ['id','profile', 'created_at']
    search_fields = ['id','profile', 'created_at']
    list_filter = ['id','profile', 'created_at']    

@admin.register(EventActivityLog)
class EventActivityLogAdmin(admin.ModelAdmin):
    list_display = ['id','profile', 'created_at','activity_type']
    search_fields = ['id','profile', 'created_at','activity_type']
    list_filter = ['id','profile', 'created_at','activity_type']      