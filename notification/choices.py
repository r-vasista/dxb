from django.db import models


class NotificationType(models.TextChoices):
    LIKE = 'like', 'Like'
    COMMENT = 'comment', 'Comment'
    FOLLOW = 'follow', 'Follow'
    FRIEND_REQUEST = 'friend_request', 'Friend Request'
    FRIEND_ACCEPT = 'friend_accept', 'Friend Accept'
    TAG = 'tag', 'Tag'
    MENTION = 'mention', 'Mention'
    SHARE = 'share', 'Share'
    POST_CREATE = 'post_create', 'Post Create'