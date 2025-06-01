# Rest Framework
from rest_framework.permissions import BasePermission

# Local imports
from user.models import Permission


class HasPermission(BasePermission):
    """
    Checks if the user has a specific permission code.
    Usage in view: permission_required = 'your_permission_code'
    """

    def has_permission(self, request, view):
        required_permission = getattr(view, 'permission_required', None)
        if not required_permission:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        # Combine role permissions + user custom permissions
        user_permissions = set(
            request.user.custom_permissions.values_list('code', flat=True)
        )
        role_permissions = set(
            Permission.objects.filter(
                role__user=request.user
            ).values_list('code', flat=True)
        )
        all_permissions = user_permissions.union(role_permissions)

        return required_permission in all_permissions
