from django.db.models import Count, Avg, Q, Max
from django.utils.timezone import now
from group.models import Group, GroupMember, GroupPost
from post.models import Post, PostReaction, Comment


def update_all_group_metrics():
    # Prefetch related posts to avoid querying them one by one
    groups = Group.objects.prefetch_related('posts')

    # Prefetch all reactions and comments for the posts in all groups in one go
    all_posts = GroupPost.objects.all()
    reactions_count_map = PostReaction.objects.values('post_id').annotate(total=Count('id'))
    comments_count_map = Comment.objects.values('post_id').annotate(total=Count('id'))

    # Build dictionaries for quick access
    reactions_dict = {item['post_id']: item['total'] for item in reactions_count_map}
    comments_dict = {item['post_id']: item['total'] for item in comments_count_map}

    for group in groups:
        posts_qs = group.posts.all()
        post_ids = [post.id for post in posts_qs]

        member_count = group.member_count

        # Count posts
        post_count = len(post_ids)

        # Sum reactions and comments for all posts in this group
        total_reactions = sum(reactions_dict.get(post_id, 0) for post_id in post_ids)
        total_comments = sum(comments_dict.get(post_id, 0) for post_id in post_ids)

        # Calculate average engagement
        if post_count > 0:
            avg_engagement = (total_reactions + total_comments) / post_count
        else:
            avg_engagement = 0.0

        # Last activity time: latest of all posts
        last_post_time = posts_qs.aggregate(latest=Max("created_at"))["latest"]

        # Trending score: weighted combination (tweak weights as needed)
        trending_score = (member_count * 0.5) + (post_count * 0.3) + (avg_engagement * 0.2)

        # Update and save group
        group.post_count = post_count
        group.avg_engagement = avg_engagement
        group.trending_score = trending_score
        group.last_activity_at = last_post_time
        group.save(update_fields=[
            "post_count", "avg_engagement", "trending_score", "last_activity_at"
        ])