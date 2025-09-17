from rest_framework.permissions import BasePermission
from .models import ChatGroup
from .utils import is_group_member

class IsChatMember(BasePermission):
    """
    Object-level permission: user must belong to the chat group.
    """

    def has_object_permission(self, request, view, obj):
        # obj is ChatGroup
        if not request.user.is_authenticated:
            return False
        try:
            profile = request.user.profile
        except Exception:
            return False
        return is_group_member(obj, profile)
