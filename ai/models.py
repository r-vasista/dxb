# Djnago imports
from django.db import models

# Local imports
from profiles.models import Profile
from ai.choices import AiUseTypes
class ArtImagePrompt(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='art_prompts')
    image = models.ImageField(upload_to='art_prompts/images/')
    prompt = models.TextField(help_text="Prompt or instruction sent to OpenAI")
    response = models.TextField(help_text="AI-generated whole response")
    response_text = models.TextField(help_text="AI-generated description and hashtags")
    gpt_model = models.CharField(max_length=200, blank=True, null=True)
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    total_tokens = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prompt by {self.profile or 'Anonymous'} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    

class BaseAIConfig(models.Model):
    use_type = models.CharField(choices=AiUseTypes.choices, max_length=50)
    gpt_model = models.CharField(max_length=200, blank=True, null=True)
    prompt = models.TextField(help_text="Prompt or instruction sent to OpenAI")
    description = models.TextField()
    
    def __str__(self):
        return f'{self.use_type, self.gpt_model}'
