from django.contrib import admin
from post.models import Post, PostMedia, Hashtag

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'title']

@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'media_type', 'file']


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']
