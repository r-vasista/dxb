from django.db.models import F

from group.models import GroupMember, GroupActionLog
from group.choices import RoleChoices
from core.models import HashTag
from core.services import extract_hashtags

def can_post_to_group(group, profile):
    try:
        member = GroupMember.objects.get(group=group, profile=profile, is_banned=False)
        return member.role in [
            RoleChoices.ADMIN,
            RoleChoices.MODERATOR,
            RoleChoices.CONTRIBUTOR
        ]
    except GroupMember.DoesNotExist:
        return False

def handle_grouppost_hashtags(post):
    """Updates hashtags for GroupPost based on its content field."""
    hashtag_text = post.content or ""
    hashtags = extract_hashtags(hashtag_text)
    post.tags.clear()
    for tag in hashtags:
        hashtag_obj, _ = HashTag.objects.get_or_create(name=tag.lower())
        post.tags.add(hashtag_obj)
        

def log_group_action(group, profile, action, description="", group_post=None, group_member=None, member_request=None):
    try:
        GroupActionLog.objects.create(
            group=group,
            profile=profile if hasattr(profile, "id") else None,
            action=action,
            description=description,
            group_post=group_post,
            group_member=group_member,
            member_request=member_request
        )
    except Exception as e:
        pass


def increment_group_member_activity(profile, group, points=1):
    """
    Increase activity_score for a group member if they are 
    contributor/moderator/admin.
    """
    try:
        member = GroupMember.objects.get(profile=profile, group=group)
        if member.role in [RoleChoices.ADMIN, RoleChoices.MODERATOR, RoleChoices.CONTRIBUTOR]:
            member.activity_score = F('activity_score') + points
            member.save(update_fields=['activity_score'])
    except GroupMember.DoesNotExist:
        pass