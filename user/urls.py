from django.urls import path

from user.views import LoginView, RoleView, GlobalRoleView, PermissionListView, RegisterAccountAPIView

urlpatterns = [
    path('registration/', RegisterAccountAPIView.as_view(), name='registration'),
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('role/', RoleView.as_view(), name='role-list'),
    path('role/<int:pk>/', RoleView.as_view(), name='role-update'),
    path('roles/global/', GlobalRoleView.as_view(), name='global-role-list-detail'),
    path('permissions-list/', PermissionListView.as_view(), name='permissions-list'),
]