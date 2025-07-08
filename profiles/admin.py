from django.contrib import admin

from profiles.models import (
    Profile, ProfileField, ProfileFieldSection, FriendRequest, ProfileCanvas, StaticProfileSection, StaticProfileField, StaticFieldValue,
    ProfileView
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'organization', 'username', 'profile_type', 'view_count']
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


@admin.register(ProfileCanvas)
class ProfileCanvasAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'image', 'display_order']
    search_fields = ['id', 'profile', 'image', 'display_order']
    list_filter = ['id', 'profile', 'image', 'display_order']


@admin.register(StaticProfileSection)
class StaticProfileSectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'display_order']
    search_fields = ['id', 'title', 'display_order']
    list_filter = ['id', 'title', 'display_order']

@admin.register(StaticProfileField)
class StaticProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'section', 'field_name', 'display_order', 'is_public']
    search_fields = ['id', 'section', 'field_name',  'display_order', 'is_public']
    list_filter = ['id', 'section', 'field_name', 'display_order', 'is_public']


@admin.register(StaticFieldValue)
class StaticFieldValueAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'static_field',]
    search_fields = ['id', 'profile', 'static_field',]
    list_filter = ['id', 'profile', 'static_field',]


@admin.register(ProfileView)
class ProfileViewAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'viewer',]
    search_fields = ['id', 'profile', 'viewer',]
    list_filter = ['id', 'profile', 'viewer',]
