from django.urls import path
from core.views import (
    LocationHierarchyAPIView, CountrySearchView, StateSearchView, CitySearchView, UpcomingFeatureAPIView, WeeklyChallengeAPIView,
    HashTagSearchAPIView ,UserStatsView, GroupStatsView, EventStatsView, PostStatsView, ProfileStatsView, NotificationStatsView,
    ProfileAnalyticsView,ProfileFilterOptionsView , PostAnalyticsView, PostFilterOptionsView, GroupAnalyticsView, GroupFilterOptionsView,
    EventAnalyticsView, EventFilterOptionsView, SuperAdminBanMemberView, SuperAdminChangeRoleView, SuperAdminDeletePostView,
    SuperAdminDeleteCommentView, SuperAdminJoinRequestApiview
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

    path("admin-dashboard/profiles/analytics/",ProfileAnalyticsView.as_view(), name="profile-analytics"),
    path("admin-dashboard/profiles/filter-options/", ProfileFilterOptionsView.as_view(), name="profile-filter-options"),

    path("admin-dashboard/posts/analytics/", PostAnalyticsView.as_view(), name="post-analytics"),
    path("admin-dashboard/posts/filter-options/", PostFilterOptionsView.as_view(), name="post-filter-options"),

    path("admin-dashboard/groups/analytics/", GroupAnalyticsView.as_view(), name="group-analytics"),
    path("admin-dashboard/groups/filter-options/", GroupFilterOptionsView.as_view(), name="group-filter-options"),

    path("admin-dashboard/events/analytics/", EventAnalyticsView.as_view(), name="event-analytics"),
    path("admin-dashboard/events/filter-options/", EventFilterOptionsView.as_view(), name="event-filter-options"),

    
    #admin Group Actions
    path("admin-dashboard/groups/members/<int:id>/ban",SuperAdminBanMemberView.as_view(),name="ban-group-member"),
    path("admin-dashboard/groups/members/<int:id>/role/",SuperAdminChangeRoleView.as_view(),name="ban-group-member"),
    path("admin-dashboard/groups/posts/<int:id>/delete/",SuperAdminDeletePostView.as_view(),name="admin-group-post-delete"),
    path("admin-dashboard/groups/comments/<int:id>/delete/",SuperAdminDeleteCommentView.as_view(),name="admin-group-comment-delete"),
    path("admin-dashboard/groups/join-requests/<int:id>/",SuperAdminJoinRequestApiview.as_view(),name="admin-group-join-request"),
    
]
    
    