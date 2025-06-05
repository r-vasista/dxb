# Django imports
from django.urls import path

# Local imports
from organization.views import (
    SendRegisterOTPIView, RegisterOrganizationAPIView, OrganizationTypeListView, IndustryTypeListView, OrganizationProfileFieldView,
    SendInviteAPIView, AcceptInviteAPIView, OrganizationMembersListAPIView, OrganizationDetailAPIView, OrganizationListAPIView
)

urlpatterns = [
    path('send-register-otp/', SendRegisterOTPIView.as_view(), name = 'send-register-otp'),
    path('register-organization/', RegisterOrganizationAPIView.as_view(), name='register-organization'),
    path('organization/<int:pk>/', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path('organizations/', OrganizationListAPIView.as_view(), name='organization-list'),
    path('organization-types/', OrganizationTypeListView.as_view(), name='organization-types'),
    path('industry-types/', IndustryTypeListView.as_view(), name='industry-types'),
    path('organization-field/<int:org_id>/',OrganizationProfileFieldView.as_view(), name='organization-field'),
    path('send-organization-invite/<int:org_id>/', SendInviteAPIView.as_view(), name='send-invite'),
    path('accept-invite/', AcceptInviteAPIView.as_view(), name='accept-invite'),
    path('members/<int:org_id>/', OrganizationMembersListAPIView.as_view(), name='organization-members'),
]