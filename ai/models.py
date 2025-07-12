from django.db import models
from profiles.models import Profile
# Create your models here.

class ArtImagePrompt(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='art_prompts')
    image = models.ImageField(upload_to='art_prompts/images/')
    prompt = models.TextField(help_text="Prompt or instruction sent to OpenAI")
    response = models.TextField(help_text="AI-generated whole response")
    response_text = models.TextField(help_text="AI-generated description and hashtags")
    gpt_model = models.CharField(max_length=500, blank=True, null=True)
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    total_tokens = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prompt by {self.profile or 'Anonymous'} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"