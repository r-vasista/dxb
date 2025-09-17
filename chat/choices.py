
from django.db import models

class ChatType(models.TextChoices):
    PERSONAL= "personal", "Personal"
    GROUP = "group", "Group"
    
class MessageType(models.TextChoices):
    TEXT = "text", "Text"
    POST = "post", "Post"
    EVENT = "event", "Event"