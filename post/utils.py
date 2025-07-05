from django.shortcuts import get_object_or_404
from django.db.models import Q

#from utils
from core.services import  get_user_profile
from profiles.choices import VisibilityStatus


#chiocies
from post.choices import (
    PostStatus,PostVisibility
)

#models 
from post.models import (
    Post, PostMedia,PostReaction,CommentLike, Comment, PostStatus, Hashtag,SharePost
)
from profiles.models import (
    Profile
)

def get_profile_from_request(profile_id=None, username=None):
    if profile_id:
        return get_object_or_404(Profile, id=profile_id)
    elif username:
        return get_object_or_404(Profile, username=username)
    else:
        raise ValueError("Either profile_id or username is required.")


def get_visible_profile_posts(request, profile, ordering=None, only_ids=False):
    user = request.user
    requester_profile = get_user_profile(user) if user.is_authenticated else None

    if profile.visibility_status != VisibilityStatus.PUBLIC:
        is_owner = requester_profile == profile
        is_friend = requester_profile in profile.friends.all() if requester_profile else False
        if not (is_owner or is_friend):
            raise PermissionError("This profile is private.")

    # Post visibility filter
    post_filter = Q(profile=profile, status=PostStatus.PUBLISHED, visibility=PostVisibility.PUBLIC)

    if user.is_authenticated:
        post_filter |= Q(
            profile=profile,
            status=PostStatus.PUBLISHED,
            visibility=PostVisibility.FOLLOWERS_ONLY,
            profile__in=requester_profile.following.all()
        )
        post_filter |= Q(
            profile=profile,
            status=PostStatus.PUBLISHED,
            visibility=PostVisibility.PRIVATE,
            created_by=user
        )

    qs = Post.objects.filter(post_filter)
    if ordering:
        qs = qs.order_by(*ordering)
    return qs.values_list('id', flat=True) if only_ids else qs

def get_post_visibility_filter(user):
    """
    Returns a Q filter object to get posts visible to the given user.
    """
    base_filter = Q(status=PostStatus.PUBLISHED, visibility=PostVisibility.PUBLIC)

    if not user or not user.is_authenticated:
        return base_filter

    requester_profile = get_user_profile(user)
    if not requester_profile:
        return base_filter

    return base_filter | Q(
        status=PostStatus.PUBLISHED,
        visibility=PostVisibility.FOLLOWERS_ONLY,
        profile__in=requester_profile.following.all()
    ) | Q(
        status=PostStatus.PUBLISHED,
        visibility=PostVisibility.PRIVATE,
        created_by=user
    )
