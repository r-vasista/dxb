from django.urls import path

from group.views import (
    GroupListAPIView, GroupPostCreateAPIView, GroupPostDetailAPIView, GroupCreateAPIView, GroupDetailAPIView, GroupAddMemberAPIView, 
    GroupMemberListAPIView, NewGroupsListAPIView, GroupUpdateAPIView
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
    path('group-members-list/<int:group_id>/', GroupMemberListAPIView.as_view(), name='group-members-list'),
    path('group-members-list/<str:group_name>/', GroupMemberListAPIView.as_view(), name='group-members-list'),

    #Group Post
    path('groups/posts/create/<int:group_id>/',GroupPostCreateAPIView.as_view(),name='create-group-post'),
    path('groups/posts/<int:group_id>/',GroupListAPIView.as_view(),name='list-group-posts'),
    path('groups/posts/<int:post_id>/',GroupPostDetailAPIView.as_view(),name='group-post-details'),
    
]
