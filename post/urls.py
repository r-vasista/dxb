from django.urls import path
from post.views import (
    PostAPIView, ProfilePostListView, AllPostsAPIView, ProfileImageMediaListView, PostReactionView, Postreactionlist,PostReactionDetailView,
    CommentView, CommentLikeToggleView, CommentDetailView,CommentReplyListView,CommentReplyView,LatestPostsAPIView,FriendsPostsAPIView,
    TrendingPostsAPIView, HashtagPostsView, HashtagsListView, PostShareView, ProfileGalleryView, UpdateGalleryOrderView,
    ProfilePostTrengingListView, MyDraftPostsView, ArtTypeListAPIView, CreatePostViewAPIView,SavedPostsListAPIView, SavePostAPIView,GlobalSearchAPIView, SearchProfilesView,
    MyHiddenCommentsAPIView,UpdateCommentVisibilityAPIView
    )


urlpatterns = [
    path('post/', PostAPIView.as_view(), name='post'),
    path('post/<int:post_id>/', PostAPIView.as_view(), name='post'),
    path('post/<str:post_slug>/', PostAPIView.as_view(), name='post'),
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
    path('hidden-comments/', MyHiddenCommentsAPIView.as_view(), name='hidden-comments'),
    path('update-comment-visibility/<int:comment_id>/', UpdateCommentVisibilityAPIView.as_view(), name='update-comment-visibility'),


    path('posts/latest/', LatestPostsAPIView.as_view(), name='latest-posts'),
    path('posts/trending/', TrendingPostsAPIView.as_view(), name='trending-posts'),
    path('posts/friends/', FriendsPostsAPIView.as_view(), name='friends-posts'),
    path('posts/hashtags/<str:hashtag_name>/', HashtagPostsView.as_view(), name='posts-hashtag'),
    path('hashtags-list/', HashtagsListView.as_view(), name='hashtags-list'),

    path('share/posts/<int:post_id>/',PostShareView.as_view(),name='post-share'),
    path('gallery/<str:profile_id>/', ProfileGalleryView.as_view(), name='gallery-profile-id'),
    path('gallery/<str:username>/', ProfileGalleryView.as_view(), name='gallery-username'),

    path('update-gallery-order/<str:profile_id>/', UpdateGalleryOrderView.as_view(), name='gallery-profile-id'),

    path('profile-trending-posts/username/<str:username>/', ProfilePostTrengingListView.as_view(), name='profile-post-trending-username'),
    path('profile-trending-posts/profile-id/<str:profile_id>/', ProfilePostTrengingListView.as_view(), name='profile-post-trending-profile_id'),

    path('posts/my-drafts/', MyDraftPostsView.as_view(), name='my-draft'),
    path('art-types/', ArtTypeListAPIView.as_view(), name='my-draft'),
    path('post-view/<int:post_id>/', CreatePostViewAPIView.as_view(), name='post-view'),

    path('saved-posts/', SavedPostsListAPIView.as_view(), name='saved-posts'),
    path('save-post/<int:post_id>/', SavePostAPIView.as_view(), name='save-post'),

    path('global-search/', GlobalSearchAPIView.as_view(), name='global-search'),

    path('search/profiles/', SearchProfilesView.as_view(), name='search-profiles'),
]
