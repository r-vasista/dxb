from django.db import models


class AiUseTypes(models.TextChoices):
        IMAGE_DESCRIPTION = 'image_description', 'Image Description'