# Django imports
from django.urls import path

# Local imports
from profiles.views import (
    ProfileView, ProfileDetailView, ProfileFieldView, ProfileFieldSectionView, SendFriendRequestView, CancelFriendRequestView,
    RespondFriendRequestView
)

urlpatterns = [
    path('profile/<str:profile_id>/', ProfileView.as_view(), name='profile'),
    path('profile-detail/<str:username>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profile-fields/<str:profile_id>/', ProfileFieldView.as_view(), name='profile-fields/'),
    path('profile-fields-section/<str:section_id>/', ProfileFieldSectionView.as_view(), name='profile-fields-section/'),
    path('send-friend-request/', SendFriendRequestView.as_view(), name='send-friend-request'),
    path('cancel-friend-request/', CancelFriendRequestView.as_view(), name='cancel-friend-request'),
    path('respond-friend-request/', RespondFriendRequestView.as_view(), name='respond-friend-request'),
]
