from group.models import GroupMember
from group.choices import RoleChoices

def can_add_members(group, profile):
    """
    Returns True if the profile is an Admin or Moderator of the group.
    Raises ValueError if the user is not part of the group.
    """
    try:
        membership = GroupMember.objects.get(group=group, profile=profile)
        return membership.role in [RoleChoices.ADMIN, RoleChoices.MODERATOR]
    except GroupMember.DoesNotExist:
        raise ValueError("You are not a member of this group.")