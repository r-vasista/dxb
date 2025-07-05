from django.urls import path
from post.views import (
    PostView, ProfilePostListView, AllPostsAPIView, ProfileImageMediaListView, PostReactionView, Postreactionlist,PostReactionDetailView,
    CommentView, CommentLikeToggleView, CommentDetailView,CommentReplyListView,CommentReplyView,LatestPostsAPIView,FriendsPostsAPIView, TrendingPostsAPIView,
    HashtagPostsView, HashtagsListView,PostShareView
    )


urlpatterns = [
    path('post/', PostView.as_view(), name='post'),
    path('post/<int:post_id>/', PostView.as_view(), name='post'),
    path('profile-posts/username/<str:username>/', ProfilePostListView.as_view(), name='profile-post-username'),
    path('profile-posts/profile-id/<str:profile_id>/', ProfilePostListView.as_view(), name='profile-post-profile_id'),
    path('all-posts/', AllPostsAPIView.as_view(), name='all-post'),
    path('profile-images/username/<str:username>/', ProfileImageMediaListView.as_view(), name='profile-images-username'),
    path('profile-images/profile-id/<str:profile_id>/', ProfileImageMediaListView.as_view(), name='profile-images-profile_id'),


    path('reactions/<int:post_id>/', PostReactionView.as_view(), name='post-reaction'),
    path('posts/<int:post_id>/reactions/', Postreactionlist.as_view(), name='post-reaction-list-by-post'),
    path('post-reactions/<int:reaction_id>/', PostReactionDetailView.as_view(), name='post-reaction-detail'),


    path('posts-comments/<int:post_id>/', CommentView.as_view(), name='post-comments'),
    path('comments-like/<int:comment_id>/', CommentLikeToggleView.as_view(), name='comment-like-toggle'),
    path('comment/<int:comment_id>/', CommentDetailView.as_view(), name='comment-detail'),
    path('comment/replies/<int:comment_id>/', CommentReplyListView.as_view(), name='comment-replies'),
    path('comment/reply/<int:comment_id>/', CommentReplyView.as_view(), name='comment-reply'),


    path('posts/latest/', LatestPostsAPIView.as_view(), name='latest-posts'),
    path('posts/trending/', TrendingPostsAPIView.as_view(), name='trending-posts'),
    path('posts/friends/', FriendsPostsAPIView.as_view(), name='friends-posts'),
    path('posts/hashtags/<str:hashtag_name>/', HashtagPostsView.as_view(), name='posts-hashtag'),
    path('hashtags-list/', HashtagsListView.as_view(), name='hashtags-list'),

    path('share/posts/<int:post_id>/',PostShareView.as_view(),name='post-share'),
]
