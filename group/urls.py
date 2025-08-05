from django.urls import path

from group.views import (
    GroupListAPIView, GroupPostCreateAPIView, GroupPostDetailAPIView, GroupCreateAPIView
)

urlpatterns = [
    path('groups/posts/create/<int:group_id>/',GroupPostCreateAPIView.as_view(),name='create-group-post'),
    path('groups/posts/<int:group_id>/',GroupListAPIView.as_view(),name='list-group-posts'),
    path('groups/posts/<int:post_id>/',GroupPostDetailAPIView.as_view(),name='group-post-details'),
    path('create-group/', GroupCreateAPIView.as_view(), name='create-group')

]
