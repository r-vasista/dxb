# Django imports
from django.urls import path

# Local imports
from profiles.views import (
    ProfileAPIView, ProfileDetailView, ProfileFieldView, ProfileFieldSectionView, SendFriendRequestView, CancelFriendRequestView,
    RespondFriendRequestView, RemoveFriendView, PendingFriendRequestsView, FollowProfileView, ListFollowersView, ListFriendsView,
    ProfileCanvasView, UnfollowProfileView, ListFollowingView, StaticFieldValueView,SearchProfilesAPIView, InspiredByFromProfileView,
    CreateProfileViewAPIView, ProfileStatsAPIView,RecentlyInteractedAPIView, EnableOrUpdateArtServiceAPIView, GetArtServiceAPIView,
    SendArtServiceInquiryAPIView, ArtServiceInquiriesAPIView, SuggestedProfilesAPIView, ReferredUsersAPIView
)

urlpatterns = [
    path('profile/<str:profile_id>/', ProfileAPIView.as_view(), name='profile'),
    path('profile-detail/<str:username>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profile-fields/<str:profile_id>/', ProfileFieldView.as_view(), name='profile-fields/'),
    path('profile-fields-section/<str:section_id>/', ProfileFieldSectionView.as_view(), name='profile-fields-section/'),
    path('profiles/search/', SearchProfilesAPIView.as_view(), name='search-profiles'),

    path('send-friend-request/', SendFriendRequestView.as_view(), name='send-friend-request'),
    path('cancel-friend-request/', CancelFriendRequestView.as_view(), name='cancel-friend-request'),
    path('respond-friend-request/', RespondFriendRequestView.as_view(), name='respond-friend-request'),
    path('remove-friend/', RemoveFriendView.as_view(), name='remove-friend'),
    path('pending-friend-requests/', PendingFriendRequestsView.as_view(), name='pending-friend-requests'),
    path('follow-profile/', FollowProfileView.as_view(), name='follow-profile'),
    path('unfollow-profile/', UnfollowProfileView.as_view(), name='unfollow-profile'),
    path('friends-list/<int:profile_id>/', ListFriendsView.as_view(), name='list-friends'),
    path('friends-list/<str:username>/', ListFriendsView.as_view(), name='list-friends'),
    path('followers-list/<int:profile_id>/', ListFollowersView.as_view(), name='list-followers'),
    path('following-list/<int:profile_id>/', ListFollowingView.as_view(), name='profile-following'),

    path('canvas/', ProfileCanvasView.as_view(), name='canvas'),
    path('canvas/<int:profile_id>/', ProfileCanvasView.as_view(), name='canvas'),
    path('canvas-update/<int:pk>/', ProfileCanvasView.as_view(), name='canvas-update'),
    path('canvas-delete/<int:pk>/', ProfileCanvasView.as_view(), name='canvas-delete'),
    
    path('static-fields/', StaticFieldValueView.as_view(), name='static-fields'),

    path('inspired-profiles/<str:profile_id>/', InspiredByFromProfileView.as_view(), name='inspired-profiles'),
    path('profile-view/<int:profile_id>/', CreateProfileViewAPIView.as_view(), name='create-profile-view'),
    path('profile-stats/', ProfileStatsAPIView.as_view(), name='profile-stats'),
    path('post/recent-interactions/', RecentlyInteractedAPIView.as_view(), name='post-recent-interactions'),
    path('art-service/<int:profile_id>/', EnableOrUpdateArtServiceAPIView.as_view(), name='art-service'),
    path('user-art-service/', GetArtServiceAPIView.as_view(), name='user-art-service'),
    path('art-service-inquire/', SendArtServiceInquiryAPIView.as_view(), name='send-art-service-inquiry'),
    path('art-service-inquiries/<int:profile_id>/', ArtServiceInquiriesAPIView.as_view(), name='art-service-inquiries/'),

    path('onboarding/suggested-profiles/', SuggestedProfilesAPIView.as_view(), name='suggested-profiles'),
    path('referred-profiles/', ReferredUsersAPIView.as_view(), name='referred-profiles'),

]
