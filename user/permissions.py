# Rest Framework
from rest_framework.permissions import BasePermission, SAFE_METHODS

# Local imports
from user.models import Permission


class HasPermission(BasePermission):
    """
    Checks if the user has permission based on HTTP method.
    Define `method_permissions = {'POST': 'perm_code', 'GET': 'perm_code'}` in the view.
    """

    def has_permission(self, request, view):
        # Support both `method_permissions` and legacy `permission_required`
        method_permissions = getattr(view, 'method_permissions', {})
        required_permission = method_permissions.get(request.method) or getattr(view, 'permission_required', None)

        if not required_permission:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        # Combine role + user custom permissions
        user_permissions = set(
            request.user.custom_permissions.values_list('code', flat=True)
        )
        role_permissions = set(
            request.user.roles.values_list('permissions__code', flat=True)
        )

        all_permissions = user_permissions.union(role_permissions)

        return required_permission in all_permissions


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS