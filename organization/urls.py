# Django imports
from django.urls import path

# Local imports
from organization.views import (
    SendRegisterOTPIView, RegisterOrganizationAPIView, OrganizationTypeListView, IndustryTypeListView, OrganizationProfileFieldView
)

urlpatterns = [
    path('send-register-otp/', SendRegisterOTPIView.as_view(), name = 'send-register-otp'),
    path('register-organization/', RegisterOrganizationAPIView.as_view(), name='register-organization'),
    path('organization-types/', OrganizationTypeListView.as_view(), name='organization-types'),
    path('industry-types/', IndustryTypeListView.as_view(), name='industry-types'),
    path('organization-field/<int:org_id>/',OrganizationProfileFieldView.as_view(), name='organization-field'),
]