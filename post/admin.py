from django.contrib import admin
from post.models import (
    Post, PostMedia, Hashtag, PostReaction, Comment, CommentLike, ArtType, PostView
)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'title', 'gallery_order', 'view_count']


@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'media_type', 'file']


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'profile', 'reaction_type']
    search_fields = ['id', 'post', 'profile', 'reaction_type']
    list_filter = ['id', 'post', 'profile', 'reaction_type']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'profile', 'content', 'parent']
    search_fields =  ['id', 'post', 'profile', 'content', 'parent']
    list_filter =  ['id', 'post', 'profile', 'content', 'parent']


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment', 'profile']
    search_fields = ['id', 'comment', 'profile']
    list_filter = ['id', 'comment', 'profile']


@admin.register(ArtType)
class ArtTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ['id', 'viewer', 'post', 'viewed_at']
    search_fields = ['id', 'viewer', 'post', 'viewed_at']
    list_filter = ['id', 'viewer', 'post', 'viewed_at']
    
