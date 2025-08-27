from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from core.models import (
    EmailConfiguration, EmailTemplate, City, Country, State, WeeklyChallenge,UpcomingFeature, FeatureStep, HashTag, Report
)
from core.resource import (
    WeeklyChallengeResource
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


@admin.register(WeeklyChallenge)
class WeeklyChallengeAdmin(ImportExportModelAdmin):
    resource_class = WeeklyChallengeResource
    list_display = ('title', 'hashtag', 'start_date', 'end_date', 'is_active')
    search_fields = ('title', 'hashtag')

class FeatureStepInline(admin.StackedInline):
    model = FeatureStep
    extra = 1
    ordering = ['order']

@admin.register(UpcomingFeature)
class UpcomingFeatureAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_at']
    inlines = [FeatureStepInline]

@admin.register(HashTag)
class HashTagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name',]
    search_fields = ['id', 'name',]
    list_filter = ['id', 'name',]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'content_type','object_id', 'reporter', 'reason']
    search_fields = ['id', 'content_type','object_id', 'reporter', 'reason']
    list_filter = ['id', 'content_type','object_id', 'reporter', 'reason']
