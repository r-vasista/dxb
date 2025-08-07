
from django.db import models

class RoleChoices(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    MODERATOR = 'moderator', 'Moderator'
    CONTRIBUTOR = 'contributor', 'Contributor'
    VIEWER = 'viewer', 'Viewer'
    

class GroupType(models.TextChoices):
    GROUP = 'group', 'Group'
    

class PrivacyChoices(models.TextChoices):
    PUBLIC = 'public', 'Public'
    PRIVATE = 'private', 'Private'


class JoiningRequestStatus(models.TextChoices):
    PENDING ='pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'