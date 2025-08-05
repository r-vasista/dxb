from group.models import GroupMember
from group.choices import RoleChoices

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
