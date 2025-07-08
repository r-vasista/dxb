from django.contrib import admin
from core.models import (
    EmailConfiguration, EmailTemplate, City, Country, State
)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'subject', 'title', 'main_content']
    search_fields = ['id', 'name', 'subject', 'title', 'main_content']
    list_filter = ['id', 'name', 'subject', 'title', 'main_content']


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'company_logo_url', 'contact_email']
    search_fields = ['id', 'company_name', 'company_logo_url', 'contact_email']
    list_filter = ['id', 'company_name', 'company_logo_url', 'contact_email']

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code']
    search_fields = ['id', 'name', 'code']
    list_filter = ['id', 'name', 'code']

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code']
    search_fields = ['id', 'name', 'code']
    list_filter = ['id', 'name', 'code']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name',]
    search_fields = ['id', 'name',]
    list_filter = ['id', 'name',]

