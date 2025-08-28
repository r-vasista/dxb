from django.urls import path
from admindashboard.views import (
    UserStatsView, GroupStatsView, EventStatsView, PostStatsView, ProfileStatsView, NotificationStatsView,
    ProfileAnalyticsView,ProfileFilterOptionsView , PostAnalyticsView, PostFilterOptionsView, GroupAnalyticsView, GroupFilterOptionsView,
    EventAnalyticsView, EventFilterOptionsView, SuperAdminBanMemberView, SuperAdminChangeRoleView, SuperAdminDeletePostView,
    SuperAdminDeleteCommentView, SuperAdminJoinRequestApiview , SuperAdminEditEventView , SuperAdminDeleteEventView ,SuperAdminDeleteEventCommentView, SuperAdminDeleteEventMediaView
)

urlpatterns = [

    # Admin Dashboard URLs
    path("users/", UserStatsView.as_view(), name="user-stats"),
    path("groups/", GroupStatsView.as_view(), name="group-stats"),
    path("events/", EventStatsView.as_view(), name="event-stats"),
    path("posts/", PostStatsView.as_view(), name="post-stats"),
    path("profiles/", ProfileStatsView.as_view(), name="profile-stats"),
    path("notifications/", NotificationStatsView.as_view(), name="notification-stats"),

    path("profiles/analytics/",ProfileAnalyticsView.as_view(), name="profile-analytics"),
    path("profiles/filter-options/", ProfileFilterOptionsView.as_view(), name="profile-filter-options"),

    path("posts/analytics/", PostAnalyticsView.as_view(), name="post-analytics"),
    path("posts/filter-options/", PostFilterOptionsView.as_view(), name="post-filter-options"),

    path("groups/analytics/", GroupAnalyticsView.as_view(), name="group-analytics"),
    path("groups/filter-options/", GroupFilterOptionsView.as_view(), name="group-filter-options"),

    path("events/analytics/", EventAnalyticsView.as_view(), name="event-analytics"),
    path("events/filter-options/", EventFilterOptionsView.as_view(), name="event-filter-options"),

    
    #admin Group Actions
    path("groups/members/<int:id>/ban",SuperAdminBanMemberView.as_view(),name="ban-group-member"),
    path("groups/members/<int:id>/role/",SuperAdminChangeRoleView.as_view(),name="ban-group-member"),
    path("groups/posts/<int:id>/delete/",SuperAdminDeletePostView.as_view(),name="admin-group-post-delete"),
    path("groups/comments/<int:id>/delete/",SuperAdminDeleteCommentView.as_view(),name="admin-group-comment-delete"),
    path("groups/join-requests/<int:id>/",SuperAdminJoinRequestApiview.as_view(),name="admin-group-join-request"),

    # admin event actions
    path("events/<int:id>/edit/", SuperAdminEditEventView.as_view(), name="admin-event-edit"),
    path("events/<int:id>/delete/", SuperAdminDeleteEventView.as_view(), name="admin-event-delete"),
    path("events/comments/<int:id>/delete/", SuperAdminDeleteEventCommentView.as_view(), name="admin-event-comment-delete"),
    path("events/media/<int:id>/delete/", SuperAdminDeleteEventMediaView.as_view(), name="admin-event-media-delete"),

    
]
    
    