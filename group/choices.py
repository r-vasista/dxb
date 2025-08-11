
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


class GroupAction(models.TextChoices):
    CREATE = "CREATE", "Group Created"
    UPDATE = "UPDATE", "Group Updated"
    DELETE = "DELETE", "Group Deleted"
    POST_CREATE = "POST_CREATE", "Post Created"
    POST_DELETE = "POST_DELETE", "Post Deleted"
    POST_UPDATE = "POST_UPDATE", "Post Update"
    TAG_ADD = "TAG_ADD", "Hashtag Added"
    TAG_REMOVE = "TAG_REMOVE", "Hashtag Removed"
    JOIN_REQUEST = "JOIN_REQUEST", "Join Request"
    MEMBER_ADD = "MEMBER_ADD", "Member add"
    MEMBER_UPDATE = "MEMBER_UPDATE", "Member update"
    MEMBER_REMOVE = "MEMBER_REMOVE", "Member remove"