from django.contrib import admin
from ai.models import (
    ArtImagePrompt
)
# Register your models here.

@admin.register(ArtImagePrompt)
class ArtImagePromptAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    search_fields = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']
    list_filter = ['id', 'profile', 'gpt_model', 'input_tokens', 'output_tokens', 'total_tokens']