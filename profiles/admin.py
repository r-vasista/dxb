from django.contrib import admin

from profiles.models import (
    Profile, ProfileField, ProfileFieldSection, FriendRequest
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'organization', 'username', 'profile_type']
    search_fields = ['id', 'user', 'organization', 'username', 'profile_type']
    list_filter = ['id', 'user', 'organization', 'username', 'profile_type']


@admin.register(ProfileField)
class ProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'section', 'field_name', 'field_type']
    search_fields = ['id', 'profile', 'field_name', 'section', 'field_type']
    list_filter = ['id', 'profile', 'field_name', 'section', 'field_type']


@admin.register(ProfileFieldSection)
class ProfileFieldSectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'title']
    search_fields = ['id', 'profile', 'title']
    list_filter = ['id', 'profile', 'title']
    

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'from_profile', 'to_profile', 'status']
    search_fields = ['id', 'from_profile', 'to_profile', 'status']
    list_filter = ['id', 'from_profile', 'to_profile', 'status']