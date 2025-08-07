from group.models import GroupMember
from group.choices import RoleChoices
from core.models import HashTag
from core.services import extract_hashtags

def can_post_to_group(group, profile):
    try:
        member = GroupMember.objects.get(group=group, profile=profile, is_banned=False)
        print(member)
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