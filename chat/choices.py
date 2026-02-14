
from django.db import models

class ChatType(models.TextChoices):
    PERSONAL= "personal", "Personal"
    GROUP = "group", "Group"
    
class MessageType(models.TextChoices):
    TEXT = "text", "Text"
    POST = "post", "Post"
    EVENT = "event", "Event"
    GROUP_POST = 'group_post', 'Group Post'
    EVENT_MEDIA ='event_media', 'Event Media'  
    