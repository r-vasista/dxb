from django.urls import path

from group.views import (
    GroupListAPIView, GroupPostCreateAPIView, GroupPostDetailAPIView, GroupCreateAPIView, GroupDetailAPIView, GroupAddMemberAPIView, 
    GroupMemberListAPIView, NewGroupsListAPIView, GroupUpdateAPIView, GroupMemberDetailAPIView,
    CreateGroupPostCommentAPIView, ParentGroupPostCommentsAPIView, ChildGroupPostCommentListAPIView,
    GroupPostLikesByIdAPIView, GroupPostLikeDetailAPIView, GroupPostCommentLikeToggleAPIView, GroupPostCommentLikeListAPIView,
    GroupJoinRequestCreateAPIView, GroupJoinRequestListAPIView, GroupJoinRequestActionAPIView,
    UpdateGroupPostCommentAPIView, DeleteGroupPostCommentAPIView, TrendingGroupsAPIView, GroupyHashTagAPIView, RecommendedGroupsAPIView, 
    GroupDeleteAPIView , GroupActionLogListAPIView,
    FlagGroupPostAPIView, GroupFlaggedPostsAPIView, GroupMemberLeaderboardListAPIView, GroupEventsListAPIView, MyGroupsListAPIView
)

urlpatterns = [
    
    # Group
    path('create-group/', GroupCreateAPIView.as_view(), name='create-group'),
    path('update-group/<int:group_id>/', GroupUpdateAPIView.as_view(), name='update-group'),
    path('delete-group/<int:group_id>/', GroupDeleteAPIView.as_view(), name='delete-group'),
    path('group-details/<int:group_id>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('group-details/<str:group_name>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('new-groups-list/', NewGroupsListAPIView.as_view(), name='new-groups-list/'),
    path('trending-groups-list/', TrendingGroupsAPIView.as_view(), name='trending-groups-list'),
    path('hashtag-groups/<str:hashtag_name>/', GroupyHashTagAPIView.as_view(), name="groups-by-hashtag-name"),
    path('recommended/', RecommendedGroupsAPIView.as_view(), name="recommended-groups"),
    path('my-groups/', MyGroupsListAPIView.as_view(), name="my-groups"),
    
    
    # Group Members
    path('join-group/<int:group_id>/', GroupJoinRequestCreateAPIView.as_view(), name='join-group'),
    path('group-requests/<int:group_id>/', GroupJoinRequestListAPIView.as_view(), name='group-requests'),
    path('respond-request/<int:group_id>/<int:request_id>/', GroupJoinRequestActionAPIView.as_view(), name='respond-requests'),
    path('add-group-member/', GroupAddMemberAPIView.as_view(), name='add-group-memeber'),
    path('group-member-detail/<int:id>/', GroupMemberDetailAPIView.as_view(), name='update-group-member'),
    path('update-group-member/', GroupMemberDetailAPIView.as_view(), name='update-group-member'),
    path('remove-group-member/', GroupMemberDetailAPIView.as_view(), name='remove-group-member'),
    path('group-members-list/<int:group_id>/', GroupMemberListAPIView.as_view(), name='group-members-list'),
    path('group-members-list/<str:group_name>/', GroupMemberListAPIView.as_view(), name='group-members-list'),
    path('group-members-Leaderboard-list/<int:group_id>/', GroupMemberLeaderboardListAPIView.as_view(), name='group-members-Leaderboard-list'),
    path('group-members-Leaderboard-list/<str:group_name>/', GroupMemberLeaderboardListAPIView.as_view(), name='group-members-Leaderboard-list'),
    
    #Group Post
    path('post/create/<int:group_id>/',GroupPostCreateAPIView.as_view(),name='create-group-post'),
    path('group-post-all/<int:group_id>/',GroupListAPIView.as_view(),name='list-group-posts'),
    path('group-post/<int:post_id>/',GroupPostDetailAPIView.as_view(),name='group-post-details'),
    
    # Flag Group POst
    path('flag-group-post/<int:post_id>/',FlagGroupPostAPIView.as_view(),name='flag-group-post'),
    path('flagged-group-posts/<int:group_id>/',GroupFlaggedPostsAPIView.as_view(),name='flag-group-post'),

    #Group_Post_Comment 
    path('group-post/<int:post_id>/comments/create/', CreateGroupPostCommentAPIView.as_view(),name='create-group-post-comment'),
    path('group-post/<int:post_id>/comments/', ParentGroupPostCommentsAPIView.as_view(),name='group-post-comments'),
    path('group-post/<int:post_id>/comments/<int:parent_id>/replies/', ChildGroupPostCommentListAPIView.as_view(),name='group-post-comment-replies'),
    path('comments/<int:comment_id>/update/', UpdateGroupPostCommentAPIView.as_view(), name='group-post-comment-update'),
    path('comments/<int:comment_id>/delete/', DeleteGroupPostCommentAPIView.as_view(), name='group-post-comment-delete' ),

    #group-post-like part
    path('groups/posts/<int:post_id>/likes/', GroupPostLikesByIdAPIView.as_view(), name='group-post-likes'),
    path('groups/posts/likes/<int:pk>/', GroupPostLikeDetailAPIView.as_view(),name='group-post-like-detail'),
    path('groups/post-comments/like-toggle/', GroupPostCommentLikeToggleAPIView.as_view(),name='group-post-comment-like-toggle' ),
    path('groups/post-comments/<int:comment_id>/likes/', GroupPostCommentLikeListAPIView.as_view(),name='group-post-comment-likes'),
    
    # Group events
    path('events-by-group/<int:group_id>/', GroupEventsListAPIView.as_view(), name='group-events-list'),

    # Group Action Log
    path('group-action-log/', GroupActionLogListAPIView.as_view(), name='group-action-log'),
]
