from django.db import models


class AiUseTypes(models.TextChoices):
        IMAGE_DESCRIPTION = 'image_description', 'Image Description'
        EVENT_TAG = 'event_tag', 'Event Tag'
        EVENT_DESCRIPTION = 'event_description', 'Event Description'
        GROUP_DESCRIPTION = 'group_description', 'Group Description'