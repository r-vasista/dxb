
from django.db import models

class ChatType(models.TextChoices):
    PERSONAL= "personal", "Personal"
    GROUP = "group", "Group"
    
