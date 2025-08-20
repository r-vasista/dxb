from django.urls import path
from core.views import (
    LocationHierarchyAPIView, CountrySearchView, StateSearchView, CitySearchView, UpcomingFeatureAPIView, WeeklyChallengeAPIView,
    HashTagSearchAPIView ,UserStatsView, GroupStatsView, EventStatsView, PostStatsView, ProfileStatsView, NotificationStatsView
)

urlpatterns = [
    path('locations/', LocationHierarchyAPIView.as_view(), name='location-hierarchy'),
    path('search/countries/', CountrySearchView.as_view(), name='search-countries'),
    path('search/states/', StateSearchView.as_view(), name='search-states'),
    path('search/cities/', CitySearchView.as_view(), name='search-cities'),
    path('weekly-challenge/', WeeklyChallengeAPIView.as_view(), name='weekly-challenge'),
    path('hashtags/search/', HashTagSearchAPIView.as_view(), name="hashtag-search"),

    path('upcoming-features/', UpcomingFeatureAPIView.as_view(), name='upcoming-features'),


    # Admin Dashboard URLs
    path("admin-dashboard/users/", UserStatsView.as_view(), name="user-stats"),
    path("admin-dashboard/groups/", GroupStatsView.as_view(), name="group-stats"),
    path("admin-dashboard/events/", EventStatsView.as_view(), name="event-stats"),
    path("admin-dashboard/posts/", PostStatsView.as_view(), name="post-stats"),
    path("admin-dashboard/profiles/", ProfileStatsView.as_view(), name="profile-stats"),
    path("admin-dashboard/notifications/", NotificationStatsView.as_view(), name="notification-stats"),
]
    
