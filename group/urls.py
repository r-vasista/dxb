from django.urls import path

from group.views import (
    GroupListAPIView, GroupPostCreateAPIView, GroupPostDetailAPIView, GroupCreateAPIView, GroupDetailAPIView, GroupAddMemberAPIView, 
    GroupMemberListAPIView, NewGroupsListAPIView, GroupUpdateAPIView, GroupMemberDetailAPIView,
    CreateGroupPostCommentAPIView, ParentGroupPostCommentsAPIView, ChildGroupPostCommentListAPIView,
    GroupPostLikesByIdAPIView, GroupPostLikeDetailAPIView, GroupPostCommentLikeToggleAPIView, GroupPostCommentLikeListAPIView
)

urlpatterns = [
    # Group
    path('create-group/', GroupCreateAPIView.as_view(), name='create-group'),
    path('update-group/<int:group_id>/', GroupUpdateAPIView.as_view(), name='update-group'),
    path('group-details/<int:group_id>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('group-details/<str:group_name>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('new-groups-list/', NewGroupsListAPIView.as_view(), name='new-groups-list/'),
    
    # Group Members
    path('add-group-member/', GroupAddMemberAPIView.as_view(), name='add-group-memeber'),
    path('update-group-member/', GroupMemberDetailAPIView.as_view(), name='update-group-member'),
    path('remove-group-member/', GroupMemberDetailAPIView.as_view(), name='remove-group-member'),
    path('group-members-list/<int:group_id>/', GroupMemberListAPIView.as_view(), name='group-members-list'),
    path('group-members-list/<str:group_name>/', GroupMemberListAPIView.as_view(), name='group-members-list'),

    #Group Post
    path('group/post/create/<int:group_id>/',GroupPostCreateAPIView.as_view(),name='create-group-post'),
    path('group/post/<int:group_id>/',GroupListAPIView.as_view(),name='list-group-posts'),
    path('group/post/<int:post_id>/',GroupPostDetailAPIView.as_view(),name='group-post-details'),

    #Group_Post_Comment 
    path('group-post/<int:post_id>/comments/create/', CreateGroupPostCommentAPIView.as_view()),
    path('group-post/<int:post_id>/comments/', ParentGroupPostCommentsAPIView.as_view()),
    path('group-post/<int:post_id>/comments/<int:parent_id>/replies/', ChildGroupPostCommentListAPIView.as_view()),

    #group-post-like part
    path('groups/posts/<int:post_id>/likes/', GroupPostLikesByIdAPIView.as_view()),
    path('groups/posts/likes/<int:pk>/', GroupPostLikeDetailAPIView.as_view()),
    path('groups/post-comments/like-toggle/', GroupPostCommentLikeToggleAPIView.as_view()),
    path('groups/post-comments/<int:comment_id>/likes/', GroupPostCommentLikeListAPIView.as_view())
]
