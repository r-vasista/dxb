from django.urls import path

from group.views import (
    GroupListAPIView, GroupPostCreateAPIView, GroupPostDetailAPIView, GroupCreateAPIView, GroupDetailAPIView
)

urlpatterns = [
    path('create-group/', GroupCreateAPIView.as_view(), name='create-group'),
    path('group-details/<int:group_id>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('group-details/<str:group_name>/', GroupDetailAPIView.as_view(), name='group-details'),
    path('groups/posts/create/<int:group_id>/',GroupPostCreateAPIView.as_view(),name='create-group-post'),
    path('groups/posts/<int:group_id>/',GroupListAPIView.as_view(),name='list-group-posts'),
    path('groups/posts/<int:post_id>/',GroupPostDetailAPIView.as_view(),name='group-post-details'),

]
