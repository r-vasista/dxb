from django.contrib import admin
from .models import Address, OrganizationType, IndustryType, Organization, OrganizationProfileField

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
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'email', 'phone_number', 'website', 'user')
        }),
        ('Classification', {
            'fields': ('organization_type', 'industry_type')
        }),
        ('Details', {
            'fields': ('description', 'logo', 'address')
        }),
        ('Status', {
            'fields': ('status', 'visibility_status')
        }),
    )


@admin.register(OrganizationProfileField)
class OrganizationProfileFieldAdmin(admin.ModelAdmin):
    list_display = ['organization', 'field_name', 'field_type']
    search_fields = ['organization', 'field_name', 'field_type']
    list_filter = ['organization', 'field_name', 'field_type']
