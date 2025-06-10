from django.contrib import admin

from profiles.models import (
    Profile, ProfileField
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'organization', 'username', 'profile_type']
    search_fields = ['id', 'user', 'organization', 'username', 'profile_type']
    list_filter = ['id', 'user', 'organization', 'username', 'profile_type']


@admin.register(ProfileField)
class ProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'field_name', 'field_type']
    search_fields = ['profile', 'field_name', 'field_type']
    list_filter = ['profile', 'field_name', 'field_type']

