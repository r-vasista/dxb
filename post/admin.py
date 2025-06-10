from django.contrib import admin
from post.models import Post, PostMedia

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'title']

@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'media_type', 'file']
