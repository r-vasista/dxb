# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.db.models import Q, F, ExpressionWrapper, IntegerField, FloatField
from django.db.models.functions import Cast

from datetime import timedelta,datetime, time
from django.utils import timezone
from django.db import IntegrityError

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly

# Local imports
from core.services import (
    success_response, error_response, get_user_profile, handle_hashtags, handle_art_styles
)
from core.pagination import PaginationMixin
from core.utils import process_media_file
from notification.task import notify_friends_of_new_post, send_comment_notification_task, send_mention_notification_task, send_post_reaction_notification_task, send_post_share_notification_task
from post.models import ReactionType, PostView, SavedPost
from profiles.models import (
    Profile
)
from profiles.serializers import ProfileSerializer
from profiles.choices import VisibilityStatus
from post.models import (
    Post, PostMedia,PostReaction,CommentLike, Comment, PostStatus, Hashtag, SharePost, ArtType
)
from post.choices import (
    PostStatus,PostVisibility
)
from post.serializers import (
    PostSerializer, ImageMediaSerializer,PostReactionSerializer,CommentSerializer, CommentLikeSerializer,
    HashtagSerializer, ProfileSearchSerializer, SavedPostSerializer, SharePostSerailizer, ArtTypeSerializer
)
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)
from organization.models import (
    OrganizationMember
)
# from notification.utils import (
#     create_dynamic_notification
# )
from core.permissions import (
    is_owner_or_org_member
)


User = get_user_model()

from .utils import extract_mentions, get_post_visibility_filter,get_profile_from_request,get_visible_profile_posts



class PostAPIView(APIView):
    """
    POST /api/posts/
    POST /api/organizations/{org_id}/posts/
    Create a post for either a user or an organization.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, org_id=None):
        try:
            profile_id = request.data.get('profile_id')

            if not profile_id:
                return Response(error_response("profile_id is required."), status=status.HTTP_400_BAD_REQUEST)

            profile = get_object_or_404(Profile, id=profile_id)

            user = request.user
            is_allowed = False

            # Case 1: Individual profile
            if profile.user and profile.user == user:
                is_allowed = True

            # Case 2: Organization profile
            elif profile.organization:
                org = profile.organization

                # Check if user is the org owner
                if org.user == user:
                    is_allowed = True
                # Check if user is a member of the org
                elif OrganizationMember.objects.filter(organization=org, user=user).exists():
                    is_allowed = True

            if not is_allowed:
                return Response(error_response("You are not allowed to post for this profile."), status=status.HTTP_403_FORBIDDEN)

            # Use request.data as-is — DO NOT copy!
            serializer = PostSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            post = serializer.save(profile=profile, created_by=request.user)
            handle_hashtags(post)
            handle_art_styles(post, request.data.get("art_types"))
            try:
                transaction.on_commit(lambda: notify_friends_of_new_post.delay(post.id))
            except:
                pass
            
            mentions = extract_mentions(" ".join(filter(None, [post.caption, post.title, post.content])))

            mentioned_profiles = Profile.objects.filter(username__in=mentions, allow_mentions=True)

            for mentioned in mentioned_profiles:
                if mentioned.id != profile.id:
                    try:
                        transaction.on_commit(lambda: send_mention_notification_task.delay(from_profile_id=profile.id, to_profile_id=mentioned.id, post_id=post.id))
                    except:
                        pass
            # Handle media files safely
            media_files = request.FILES.getlist('media_files')
            for idx, media_file in enumerate(media_files):
                processed_file, media_type = process_media_file(media_file)
                PostMedia.objects.create(
                    post=post,
                    file=processed_file,
                    media_type=media_type,
                    order=idx
                )

            return Response(success_response(PostSerializer(post, context={'request': request}).data), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    def put(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)

            if post.created_by != request.user:
                return Response(error_response("You are not allowed to update this post."), status=status.HTTP_403_FORBIDDEN)
            

            serializer = PostSerializer(post, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            handle_hashtags(post)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)
            user = request.user
            requester_profile = get_user_profile(user) if user.is_authenticated else None

            if post.visibility == PostVisibility.FOLLOWERS_ONLY:
                if not user.is_authenticated or post.profile not in requester_profile.following.all():
                    return Response(error_response("You are not allowed to view this post."), status=status.HTTP_403_FORBIDDEN)

            elif post.visibility == PostVisibility.PRIVATE:
                if not user.is_authenticated or post.created_by != user:
                    return Response(error_response("This post is private."), status=status.HTTP_403_FORBIDDEN)

            serializer = PostSerializer(post, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    def delete(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)

            if post.created_by != request.user:
                return Response(error_response("You are not allowed to delete this post."), status=status.HTTP_403_FORBIDDEN)

            post.delete()
            return Response(success_response("Post deleted successfully."), status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilePostListView(APIView, PaginationMixin):
    """
    GET /api/profiles/{profile_id}/posts/
    GET /api/profiles/username/{username}/posts/
    Fetch all posts created by a specific profile (with pagination).
    """
    def get(self, request, profile_id=None, username=None):
        try:
            profile = get_profile_from_request(profile_id, username)

            posts = get_visible_profile_posts(
                request, profile, ordering=['-is_pinned', '-created_at']
            )

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
          

class AllPostsAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            visibility_filter = get_post_visibility_filter(request.user)

            posts = Post.objects.filter(visibility_filter).order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProfileImageMediaListView(APIView, PaginationMixin):
    """
    GET /api/profiles/{profile_id}/media/images/
    GET /api/profiles/username/{username}/media/images/
    Returns only image media files for a given profile, respecting post and profile visibility.
    """
    def get(self, request, profile_id=None, username=None):
        try:
            profile = get_profile_from_request(profile_id, username)
            allowed_post_ids = get_visible_profile_posts(request, profile, only_ids=True)

            image_media = PostMedia.objects.filter(
                post_id__in=allowed_post_ids,
                media_type='image'
            ).order_by('order')

            paginated_queryset = self.paginate_queryset(image_media, request)
            serializer = ImageMediaSerializer(paginated_queryset, many=True)
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostReactionView(APIView):
    """
    POST /api/posts/{post_id}/reactions/

    Authenticated endpoint to create or update a user's reaction to a post.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)
            profile = get_user_profile(request.user)

            if not post.allow_reactions:
                return Response(error_response("Reactions are Disabled for this Post"),status=status.HTTP_403_FORBIDDEN)

            # Clean and validate reaction_type
            reaction_type = request.data.get("reaction_type", "").strip().lower()
            if reaction_type not in ReactionType.values:
                return Response(
                    error_response(f"Invalid reaction_type. Allowed values: {', '.join(ReactionType.values)}"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch existing reaction
            existing_reaction = post.reactions.filter(profile=profile).first()

            if existing_reaction:
                if existing_reaction.reaction_type == reaction_type:
                    # Same reaction exists — remove it (toggle off)
                    existing_reaction.delete()

                    # Update post reaction count
                    post.reaction_count = post.reactions.count()
                    post.save(update_fields=["reaction_count"])
                    return Response(success_response("Reaction removed."), status=status.HTTP_200_OK)

                # Update reaction type
                serializer = PostReactionSerializer(existing_reaction, data={"post": post.id,"profile": profile.id,"reaction_type": reaction_type}, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(success_response(serializer.data), status=status.HTTP_200_OK)

            # Create new reaction
            serializer = PostReactionSerializer(data={"post": post.id,"profile": profile.id,"reaction_type": reaction_type})
            serializer.is_valid(raise_exception=True)
            post_reaction = serializer.save()
            try: 
                transaction.on_commit(lambda: send_post_reaction_notification_task.delay(post_reaction.id))
            except:
                pass

            # Optional: update reaction count on the post
            post.reaction_count = post.reactions.count()
            post.save(update_fields=["reaction_count"])

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   

class PostReactionDetailView(APIView):
    """
    GET /api/post-reactions/{reaction_id}/
    DELETE /api/post-reactions/{reaction_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, request, reaction_id):
        profile = get_user_profile(request.user)
        return get_object_or_404(PostReaction, id=reaction_id, profile=profile)

    def get(self, request, reaction_id):
        reaction = self.get_object(request, reaction_id)
        serializer = PostReactionSerializer(reaction)
        return Response(success_response(serializer.data), status=status.HTTP_200_OK)

    def delete(self, request, reaction_id):
        reaction = self.get_object(request, reaction_id)
        post = reaction.post
        reaction.delete()

        # Optional: update post.reaction_count
        post.reaction_count = post.reactions.count()
        post.save(update_fields=['reaction_count'])

        return Response(success_response("Reaction deleted."), status=status.HTTP_204_NO_CONTENT)
    
class Postreactionlist(APIView, PaginationMixin):
    """
    GET /api/posts/{post_id}/reactions/
    Fetch all reactions for a specific post with pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)
            reactions = post.reactions.all().order_by('-created_at')

            # Apply pagination
            paginated_queryset = self.paginate_queryset(reactions, request)
            serializer = PostReactionSerializer(paginated_queryset, many=True)

            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CommentView(APIView, PaginationMixin):
    """
    GET /api/posts/{post_id}/comments/
    POST /api/posts/{post_id}/comments/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)
            comments = post.comments.filter(parent=None,is_approved=True).select_related('profile').order_by('-created_at')

            paginated_queryset = self.paginate_queryset(comments, request)
            serializer = CommentSerializer(paginated_queryset, many=True)

            return self.get_paginated_response(serializer.data)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)
            profile = get_user_profile(request.user)
            if not post.allow_comments:
                return Response(error_response("Comments are disable for this Post"),status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['post'] = post.id
            data['profile'] = profile.id
            data['is_approved'] = True

            serializer = CommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.save()
            try:
                transaction.on_commit(lambda: send_comment_notification_task.delay(comment.id))
            except:
                pass

            post.comment_count = post.comments.count()
            post.save(update_fields=["comment_count"])

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CommentLikeToggleView(APIView):
    """
    POST /api/comments/{comment_id}/like/
    Toggles like for the given comment by the current user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        try:
            comment = get_object_or_404(Comment, id=comment_id)
            profile = get_user_profile(request.user)

            like, created = CommentLike.objects.get_or_create(comment=comment, profile=profile)

            if not created:
                like.delete()
                comment.like_count = comment.likes.count()
                comment.save(update_fields=["like_count"])
                return Response(success_response("Unliked"), status=status.HTTP_200_OK)

            comment.like_count = comment.likes.count()
            comment.save(update_fields=["like_count"])
            return Response(success_response("Liked"), status=status.HTTP_201_CREATED)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CommentDetailView(APIView):
    """
    GET /api/comments/{comment_id}/
    DELETE /api/comments/{comment_id}/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, request, comment_id):
        profile = get_user_profile(request.user)

        comment = get_object_or_404(Comment, id=comment_id)

        # Allow if the user is the comment owner or the post owner
        if comment.profile == profile or comment.post.profile == profile:
            return comment

        raise Http404("You do not have permission to access this comment.")

    def get(self, request, comment_id):
        try:
            comment = self.get_object(request, comment_id)
            serializer = CommentSerializer(comment)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, comment_id):
        try:
            comment = self.get_object(request, comment_id)
            post = comment.post
            comment.delete()

            post.comment_count = post.comments.count()
            post.save(update_fields=["comment_count"])

            return Response(success_response("Comment deleted."), status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentReplyView(APIView):
    """
    POST /api/comments/{comment_id}/reply/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        try:
            parent_comment = get_object_or_404(Comment, id=comment_id)
            post = parent_comment.post
            profile = get_user_profile(request.user)

            data = request.data.copy()
            data['post'] = post.id
            data['profile'] = profile.id
            data['parent'] = parent_comment.id
            data['is_approved'] = True

            serializer = CommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.save()
            try:
                transaction.on_commit(lambda: send_comment_notification_task.delay(comment.id))
            except:
                pass
            # Update reply count
            parent_comment.reply_count = parent_comment.replies.filter(is_approved=True).count()
            parent_comment.save(update_fields=['reply_count'])

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentReplyListView(APIView, PaginationMixin):
    """
    GET /api/comments/{comment_id}/replies/
    Fetch all replies for a specific comment with pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, comment_id):
        try:
            parent_comment = get_object_or_404(Comment, id=comment_id)
            replies = parent_comment.replies.filter(is_approved=True).select_related('profile').order_by('-created_at')

            paginated_queryset = self.paginate_queryset(replies, request)
            serializer = CommentSerializer(paginated_queryset, many=True)

            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class TrendingPostsAPIView(APIView, PaginationMixin):
    """
    GET /api/posts/trending/
    Returns trending posts sorted by reactions, views, comments, shares, while enforcing visibility.
    """
    def get(self, request):
        try:
            visibility_filter = get_post_visibility_filter(request.user)

            posts = Post.objects.annotate(
                    trending_score=ExpressionWrapper(
                        F('reaction_count') +
                        (F('comment_count') * 2) +
                        (F('share_count') * 3) +
                        ExpressionWrapper(Cast(F('view_count'), FloatField()) / 5, output_field=FloatField()),
                        output_field=FloatField()
                    )
                ).filter(visibility_filter).order_by('-trending_score')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class FriendsPostsAPIView(APIView, PaginationMixin):
    """
    GET /api/posts/friends/
    Shows published posts from your friends, with visibility enforced.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            friend_profiles = profile.friends.all()
            following_profiles = profile.following.all()

            posts = Post.objects.filter(
                status=PostStatus.PUBLISHED
            ).filter(
                Q(profile__in=friend_profiles, visibility=PostVisibility.PUBLIC) |
                Q(profile__in=friend_profiles.intersection(following_profiles), visibility=PostVisibility.FOLLOWERS_ONLY) |
                Q(profile__in=friend_profiles, visibility=PostVisibility.PRIVATE, created_by=request.user)
            ).order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Profile.DoesNotExist:
            return Response(error_response("Profile not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LatestPostsAPIView(APIView, PaginationMixin):
    """
    GET /api/posts/latest/
    Returns latest published posts, respecting post visibility.
    """
    def get(self, request):
        try:
            visibility_filter = get_post_visibility_filter(request.user)

            posts = Post.objects.filter(visibility_filter).order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class HashtagPostsView(APIView, PaginationMixin):
    """
    GET /api/hashtags/<hashtag_name>/posts/
    Returns paginated posts under the given hashtag, respecting visibility.
    """
    def get(self, request, hashtag_name):
        try:
            hashtag = get_object_or_404(Hashtag, name=hashtag_name.lower())

            visibility_filter = get_post_visibility_filter(request.user)

            posts = hashtag.posts.filter(visibility_filter).order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class HashtagsListView(APIView, PaginationMixin):
    """
    GET /api/hashtags-list/?search=art
    Returns a paginated list of hashtags, filtered by optional search query.
    """
    def get(self, request):
        try:
            search_query = request.query_params.get('search', '').strip()
            
            hashtags = Hashtag.objects.all()
            if search_query:
                hashtags = hashtags.filter(name__icontains=search_query)

            paginated_queryset = self.paginate_queryset(hashtags, request)
            serializer = HashtagSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostShareView(APIView):
    """
    Post/share/posts/{post_id}

    Authenticated endpoint to share a post by a profile 
    Only one share per profile is allowed; duplicate attempts are ignored
    
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try: 
            post=get_object_or_404(Post,id=post_id)
            profile= get_user_profile(request.user)

            existing_share = SharePost.objects.filter(post=post, profile=profile).first()
            if existing_share:
                return Response(success_response("Post already shared. "),status=status.HTTP_201_CREATED)
            
            serializer=SharePostSerailizer(data={"post":post.id,"profile":profile.id})
            serializer.is_valid(raise_exception=True)
            share = serializer.save()

            post.share_count=SharePost.objects.filter(post=post).count()
            post.save(update_fields=["share_count"])
            try:
                transaction.on_commit(lambda: send_post_share_notification_task.delay(share.id))
            except:
                pass 

            return Response(success_response(serializer.data),status=status.HTTP_201_CREATED)
        
        
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileGalleryView(APIView, PaginationMixin):
    """
    GET /api/profiles/{profile_id}/gallery/?art_type_ids=1,2&sort=popular

    Filters:
    - art_type_ids: Filter by one or more ArtType IDs (comma separated)
    - sort: 'recent', 'popular', or 'gallery_order' (default: gallery_order)
    """

    def get(self, request, profile_id=None, username=None):
        try:
            profile = get_profile_from_request(profile_id, username)
            posts = get_visible_profile_posts(request, profile)

            # Apply art type filter
            art_type_ids = request.query_params.get('art_type_ids')
            if art_type_ids:
                art_type_ids = [int(id.strip()) for id in art_type_ids.split(',') if id.strip().isdigit()]
                posts = posts.filter(art_types__in=art_type_ids).distinct()

            # Apply sorting
            sort = request.query_params.get('sort', 'gallery_order')
            if sort == 'popular':
                ordering = ['-reaction_count', '-view_count', '-comment_count', '-created_at']
            elif sort == 'recent':
                ordering = ['-created_at']
            else:  # Default: gallery_order
                ordering = ['gallery_order', '-created_at']

            posts = posts.order_by(*ordering)

            # Paginate & serialize
            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateGalleryOrderView(APIView):
    """
    POST /api/profiles/{profile_id}/gallery/order/

    Body: { "ordered_post_ids": [5, 2, 9, 3] }
    Updates gallery order for posts belonging to this profile.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            allowed = is_owner_or_org_member(profile=profile, user=request.user)

            if not allowed:
                return Response(error_response("Permission denied."), status=status.HTTP_403_FORBIDDEN)

            ordered_ids = request.data.get('ordered_post_ids', [])
            if not isinstance(ordered_ids, list):
                return Response(error_response("Invalid format. Provide list of post IDs."), status=status.HTTP_400_BAD_REQUEST)

            for index, post_id in enumerate(ordered_ids):
                Post.objects.filter(id=post_id, profile=profile).update(gallery_order=index)

            return Response(success_response("Gallery order updated."), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilePostTrengingListView(APIView, PaginationMixin):
    """
    GET /api/profiles/{profile_id}/posts/trending/
    Trending posts from a specific profile, ordered by engagement.
    """
    def get(self, request, profile_id=None, username=None):
        try:
            profile = get_profile_from_request(profile_id, username)
            
            ordering = [
                '-is_pinned', '-reaction_count', '-view_count',
                '-comment_count', '-created_at', '-share_count'
            ]
            posts = get_visible_profile_posts(request, profile, ordering=ordering)

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MyDraftPostsView(APIView, PaginationMixin):
    """
    GET /api/posts/my-drafts/
    Returns draft posts created by the current user in the last 7 days.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            seven_days_ago = timezone.now() - timedelta(days=7)

            # Auto delete older drafts
            Post.objects.filter(
                status=PostStatus.DRAFT,
                created_by=user,
                created_at__lt=seven_days_ago
            ).delete()

            recent_drafts = Post.objects.filter(
                status=PostStatus.DRAFT,
                created_by=user,
                created_at__gte=seven_days_ago
            ).order_by('-created_at')

            paginated = self.paginate_queryset(recent_drafts, request)
            serializer = PostSerializer(paginated, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ArtTypeListAPIView(APIView, PaginationMixin):
    """
    GET /api/art-types/?q=painting
    Returns paginated ArtTypes, optionally filtered by search.
    """
    def get(self, request):
        try:
            query = request.query_params.get('q', '')
            queryset = ArtType.objects.all()
            if query:
                queryset = queryset.filter(Q(name__icontains=query) | Q(slug__icontains=query))

            queryset = queryset.order_by('name')
            paginated = self.paginate_queryset(queryset, request)
            serializer = ArtTypeSerializer(paginated, many=True)

            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreatePostViewAPIView(APIView):
    """
    POST /api/posts/<post_id>/view/

    Tracks a view on a post and increments view_count.
    Accepts both authenticated and anonymous users.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, post_id):
        try:
            post = get_object_or_404(Post.objects.select_related("profile", "created_by"), id=post_id)
            viewer = get_user_profile(request.user) if request.user.is_authenticated else None

            # Prevent self-views from being tracked
            if viewer and post.profile == viewer:
                return Response(success_response("Self view ignored"), status=200)

            # Save post view
            PostView.objects.create(post=post, viewer=viewer)

            # Update view count
            post.view_count = post.view_count + 1
            post.save(update_fields=["view_count"])

            return Response(success_response("Post view tracked"), status=201)
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
                return Response(success_response("Post view tracked already"), status=201)
        except Exception as e:
            return Response(error_response(str(e)), status=500)

class SavePostAPIView(APIView):
    """ POST /api/posts/{post_id}/save/
    Authenticated endpoint to save or unsave a post.
    If the post is already saved, it will be unsaved.               
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            profile = get_user_profile(request.user)
            if not profile:
                raise Http404("Profile not found.")

            try:
                post = Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                raise Http404("Post not found.")

            saved_obj, created = SavedPost.objects.get_or_create(profile=profile, post=post)
            if not created:
                saved_obj.delete()
                return Response({"message": "Post unsaved"}, status=status.HTTP_200_OK)

            return Response({"message": "Post saved"}, status=status.HTTP_201_CREATED)

        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
class SavedPostsListAPIView(APIView, PaginationMixin):
    """
    GET /api/saved-posts/
    Returns a list of posts saved by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            if not profile:
                raise Http404("Profile not found.")

            saved_posts = SavedPost.objects.filter(profile=profile).select_related('post').order_by('-created_at')
            page = self.paginate_queryset(saved_posts, request)
            serializer = SavedPostSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GlobalSearchAPIView(APIView, PaginationMixin):
    """
    GET /api/global-search/?search=art&type=post&start_date=2025-07-01&end_date=2025-07-10
    Query Params:
    - search: keyword
    - type: post | profile | hashtag | all
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """

    permission_classes = []

    def get(self, request):
        try:
            search = request.query_params.get('search', '').strip()
            search_type = request.query_params.get('type', 'all').lower()
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
            end_date = datetime.combine(datetime.strptime(end_date_str, "%Y-%m-%d").date(), time.max) if end_date_str else None

            data = {}

            # --- POSTS ---
            if search_type in ['post', 'all']:
                posts = Post.objects.filter(
                    visibility=PostVisibility.PUBLIC,
                    profile__visibility_status=VisibilityStatus.PUBLIC
                )

                if search:
                    posts = posts.filter(
                        Q(title__icontains=search) |
                        Q(caption__icontains=search) |
                        Q(hashtags__name__icontains=search)
                    )

                if start_date:
                    posts = posts.filter(created_at__gte=start_date)
                if end_date:
                    posts = posts.filter(created_at__lte=end_date)

                paginated_posts = self.paginate_queryset(posts.order_by('-created_at'), request)
                data['posts'] = PostSerializer(paginated_posts, many=True, context={'request': request}).data

            # --- PROFILES ---
            if search_type in ['profile', 'all']:


                if search:
                    profiles = Profile.objects.filter(
                        Q(username__icontains=search)
                    )
                else:
                    profiles = Profile.objects.all()

                paginated_profiles = self.paginate_queryset(profiles.order_by('-created_at'), request)
                data['profiles'] = ProfileSerializer(paginated_profiles, many=True, context={'request': request}).data

            # --- HASHTAGS ---
            if search_type in ['hashtag', 'all']:
                hashtags = Hashtag.objects.all()
                if search:
                    hashtags = hashtags.filter(name__icontains=search)

                paginated_hashtags = self.paginate_queryset(hashtags.order_by('-id'), request)
                data['hashtags'] = HashtagSerializer(paginated_hashtags, many=True, context={'request': request}).data

            return Response(success_response(data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SearchProfilesView(APIView):
    """
    GET /api/profiles/search/?q=<query>
    Returns a list of profiles matching username .
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query=request.GET.get('q', '').strip()
        if not query:
            return Response(error_response("Query parameter 'q' is required."), status=status.HTTP_400_BAD_REQUEST)
        try:
            profiles = Profile.objects.filter(username__icontains=query, allow_mentions=True).order_by('username')
            serializer = ProfileSearchSerializer(profiles, many=True, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class MyHiddenCommentsAPIView(APIView):
    """
    GET /api/comments/hidden/
    Returns all comments created by the user that are currently hidden (is_approved=False)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            hidden_comments = Comment.objects.filter(profile=profile, is_approved=False).select_related('post')
            serializer = CommentSerializer(hidden_comments, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateCommentVisibilityAPIView(APIView):
    """
    PATCH /api/comments/visibility/{comment_id}/
    Body: { "is_approved": true }  # true = unhide, false = hide
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, comment_id):
        try:
            profile = get_user_profile(request.user)
            comment = get_object_or_404(Comment, id=comment_id)

            if comment.profile != profile:
                raise PermissionError("You are not allowed to change this comment.")

            is_approved = request.data.get('is_approved')
            if isinstance(is_approved, str):
                is_approved = is_approved.lower() == 'true'
            if is_approved not in [True, False]:
                raise ValueError("Invalid value for 'is_approved'. Must be true or false.")

            comment.is_approved = is_approved
            comment.save(update_fields=['is_approved'])

            return Response({
                "message": "Comment updated successfully.",
                "is_approved": comment.is_approved
            }, status=200)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
