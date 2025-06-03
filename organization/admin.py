from django.contrib import admin
from organization.models import (
    Address, OrganizationType, IndustryType, Organization, OrganizationProfileField, OrganizationInvite, OrganizationMember
)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'city', 'state', 'country', 'postal_code')
    search_fields = ('address', 'city', 'state', 'country', 'postal_code')
    list_filter = ('city', 'state', 'country')


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(IndustryType)
class IndustryTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'email', 'phone_number',
        'organization_type', 'industry_type',
        'status', 'visibility_status',
    )
    search_fields = ('name', 'email', 'phone_number', 'slug')
    list_filter = (
        'organization_type', 'industry_type',
        'status', 'visibility_status',
    )
    readonly_fields = ('slug',)
    autocomplete_fields = ('address', 'organization_type', 'industry_type')


@admin.register(OrganizationProfileField)
class OrganizationProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['organization', 'field_name', 'field_type']
    search_fields = ['organization', 'field_name', 'field_type']
    list_filter = ['organization', 'field_name', 'field_type']


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(admin.ModelAdmin):
    list_display = ['organization', 'email', 'status', 'invited_by', 'expires_at']
    search_fields = ['organization', 'email', 'status', 'invited_by', 'expires_at']
    list_filter = ['organization', 'email', 'status', 'invited_by', 'expires_at']


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ['organization', 'user']
    search_fields = ['organization', 'user']
    list_filter = ['organization', 'user']
