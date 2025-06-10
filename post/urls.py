from django.urls import path
from post.views import PostView, ProfilePostListView, AllPostsAPIView

urlpatterns = [
    path('post/', PostView.as_view(), name='post'),
    path('post/<int:post_id>/', PostView.as_view(), name='post'),
    path('profile-posts/username/<str:username>/', ProfilePostListView.as_view(), name='profile-post-username'),
    path('profile-posts/profile-id/<str:profile_id>/', ProfilePostListView.as_view(), name='profile-post-profile_id'),
    path('all-posts/', AllPostsAPIView.as_view(), name='all-post'),
]
