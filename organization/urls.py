# Django imports
from django.urls import path

# Local imports
from organization.views import (
    SendRegisterOTPIView, RegisterOrganizationAPIView
)

urlpatterns = [
    path('send-register-otp/', SendRegisterOTPIView.as_view(), name = 'send-register-otp'),
    path('register-organization/', RegisterOrganizationAPIView.as_view(), name='register-organization')
]