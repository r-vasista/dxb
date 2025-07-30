from django.contrib import admin
from ai.models import (
    ArtImagePrompt, BaseAIConfig, EventTagPrompt, EventDescriptionPrompt
)
# Register your models here.

@admin.register(ArtImagePrompt)
class ArtImagePromptAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    search_fields = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    list_filter = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']


@admin.register(BaseAIConfig)
class BaseAIConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'use_type', 'gpt_model']
    search_fields =  ['id', 'use_type', 'gpt_model']
    list_filter =  ['id', 'use_type', 'gpt_model']


@admin.register(EventTagPrompt)
class EventTagPromptAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    search_fields = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    list_filter = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']

@admin.register(EventDescriptionPrompt)
class EventDescriptionPromptAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    search_fields = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    list_filter = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
