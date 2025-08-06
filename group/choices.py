
from django.db import models

class RoleChoices(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MODERATOR = 'moderator', 'Moderator'
    CONTRIBUTOR = 'contributor', 'Contributor'
    VIEWER = 'viewer', 'Viewer'
    

class GroupType(models.TextChoices):
    GROUP = 'group', 'Group'
    