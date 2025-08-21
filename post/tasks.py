# posts/tasks.py

from celery import shared_task
from django.utils import timezone
from post.models import Post
from post.choices import PostStatus

@shared_task
def publish_scheduled_post(post_id):
    try:
        post = Post.objects.get(id=post_id)
        if post.status == PostStatus.SCHEDULED and post.published_at is None:
            post.status = PostStatus.PUBLISHED
            post.published_at = timezone.now()
            post.save(update_fields=["status", "published_at"])
            return f"Post {post_id} published at {post.published_at}"
        return f"Post {post_id} already published or not scheduled"
    except Post.DoesNotExist:
        return f"Post {post_id} not found"