# Django imports
from django.urls import path

# Local imports
from profiles.views import (
    ProfileView, ProfileDetailView, ProfileFieldView
)

urlpatterns = [
    path('profile/<str:profile_id>/', ProfileView.as_view(), name='profile'),
    path('profile-detail/<str:username>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profile-fields/<str:profile_id>/', ProfileFieldView.as_view(), name='profile-fields/'),
]
