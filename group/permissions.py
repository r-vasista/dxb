from rest_framework.permissions import BasePermission
from group.models import GroupMember
from group.choices import RoleChoices
from core.services import get_user_profile

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
    
class IsGroupAdminOrModerator(BasePermission):
    """
    Allows access only to group Admin or Moderator.
    """

    def has_object_permission(self, request, view, obj):
        """
        `obj` will be the Group instance.
        """
        if not request.user.is_authenticated:
            return False
        
        try:
            membership = GroupMember.objects.get(group=obj, profile=get_user_profile(request.user))
            return membership.role in [RoleChoices.ADMIN, RoleChoices.MODERATOR]
        except GroupMember.DoesNotExist:
            return False


class IsGroupAdmin(BasePermission):
    """
    Allows access only to group Admin.
    """

    def has_object_permission(self, request, view, obj):
        """
        `obj` is expected to be a Group instance.
        """
        if not request.user.is_authenticated:
            return False

        try:
            membership = GroupMember.objects.get(group=obj, profile=get_user_profile(request.user))
            return membership.role == RoleChoices.ADMIN
        except GroupMember.DoesNotExist:
            return False
