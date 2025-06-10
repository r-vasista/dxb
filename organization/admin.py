from django.contrib import admin
from organization.models import (
    Address, OrganizationType, IndustryType, Organization, OrganizationProfileField, OrganizationInvite, OrganizationMember
)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'address', 'city', 'state', 'country', 'postal_code')
    search_fields = ('id', 'address', 'city', 'state', 'country', 'postal_code')
    list_filter = ('id', 'city', 'state', 'country')


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    search_fields = ('id', 'name',)
    list_filter = ('id', 'is_active',)


@admin.register(IndustryType)
class IndustryTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    search_fields = ('id', 'name',)
    list_filter = ('id', 'is_active',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'slug', 'email', 'phone_number',
        'organization_type', 'industry_type',
        'status',
    )
    search_fields = ('id', 'name', 'email', 'phone_number', 'slug')
    list_filter = (
        'id', 'organization_type', 'industry_type',
        'status',
    )
    readonly_fields = ('slug',)
    autocomplete_fields = ('address', 'organization_type', 'industry_type')


@admin.register(OrganizationProfileField)
class OrganizationProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'field_name', 'field_type']
    search_fields = ['organization', 'field_name', 'field_type']
    list_filter = ['organization', 'field_name', 'field_type']


@admin.register(OrganizationInvite)
class OrganizationInviteAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'email', 'status', 'invited_by', 'expires_at']
    search_fields = ['organization', 'email', 'status', 'invited_by', 'expires_at']
    list_filter = ['organization', 'email', 'status', 'invited_by', 'expires_at']


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'user']
    search_fields = ['organization', 'user']
    list_filter = ['organization', 'user']
