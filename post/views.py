# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.utils.dateparse import parse_datetime


# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny

# Local imports
from core.services import success_response, error_response, get_user_profile, handle_hashtags
from core.pagination import PaginationMixin
from post.models import ReactionType
from profiles.models import (
    Profile
)
from profiles.serializers import ProfileSerializer
from post.models import (
    Post, PostMedia,PostReaction,CommentLike, Comment, PostStatus, Hashtag
)
from post.choices import (
    PostStatus
)
from post.serializers import (
    PostSerializer, ImageMediaSerializer,PostReactionSerializer,CommentSerializer, CommentLikeSerializer
)
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)

User = get_user_model()

class PostView(APIView):
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

            # Use request.data as-is — DO NOT copy!
            serializer = PostSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            post = serializer.save(profile=profile, created_by=request.user)
            handle_hashtags(post)

            # Handle media files safely
            media_files = request.FILES.getlist('media_files')
            for idx, media_file in enumerate(media_files):
                PostMedia.objects.create(
                    post=post,
                    file=media_file,
                    media_type=media_file.content_type.split('/')[0],
                    order=idx
                )

            return Response(success_response(PostSerializer(post).data), status=status.HTTP_201_CREATED)

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
            if profile_id:
                profile = get_object_or_404(Profile, id=profile_id)
            elif username:
                profile = get_object_or_404(Profile, username=username)
            else:
                return Response(error_response("username or profile id is required"), status=status.HTTP_400_BAD_REQUEST)

            posts = Post.objects.filter(profile=profile.id).order_by('-created_at')

            # Apply pagination
            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})

            return self.get_paginated_response(serializer.data)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class AllPostsAPIView(APIView, PaginationMixin):
    
    def get(self, request):
        try:

            posts = Post.objects.all().order_by('-created_at')

            # Apply pagination
            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})

            return self.get_paginated_response(serializer.data)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ProfileImageMediaListView(APIView, PaginationMixin):
    """
    GET /api/profiles/{profile_id}/media/images/
    Returns only image media files for a given profile.
    """

    def get(self, request, profile_id=None, username=None):
        try:
            if profile_id:
                profile = get_object_or_404(Profile, id=profile_id)
            elif username:
                profile = get_object_or_404(Profile, username=username)
            else:
                return Response(error_response("username or profile id is required"), status=status.HTTP_400_BAD_REQUEST)

            # Get all post IDs for this profile
            post_ids = Post.objects.filter(profile=profile).values_list('id', flat=True)

            # Filter PostMedia by those post IDs and media_type='image'
            image_media = PostMedia.objects.filter(
                post_id__in=post_ids
            ).order_by('order')

            paginated_queryset = self.paginate_queryset(image_media, request)
            serializer = ImageMediaSerializer(paginated_queryset, many=True)

            return self.get_paginated_response(serializer.data)

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
                    return Response(success_response("Already Reacted."), status=status.HTTP_200_OK)

                # Update reaction type
                serializer = PostReactionSerializer(existing_reaction, data={"post": post.id,"profile": profile.id,"reaction_type": reaction_type}, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                return Response(success_response(serializer.data), status=status.HTTP_200_OK)

            # Create new reaction
            serializer = PostReactionSerializer(data={"post": post.id,"profile": profile.id,"reaction_type": reaction_type})
            serializer.is_valid(raise_exception=True)
            serializer.save()


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
            comments = post.comments.filter(parent=None).select_related('profile').order_by('-created_at')

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

            serializer = CommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

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
        return get_object_or_404(Comment, id=comment_id, profile=profile)

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
            profile= get_user_profile(request.user)
            comment = self.get_object( comment_id, profile=profile)
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

            serializer = CommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Update reply count
            parent_comment.reply_count = parent_comment.replies.count()
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
    
    def get(self, request):
        try:
            posts = Post.objects.filter(status=PostStatus.PUBLISHED)\
                .order_by('-reaction_count', '-view_count', '-comment_count')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FriendsPostsAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            friend_profiles = profile.friends.all()
            
            posts = Post.objects.filter(profile__in=friend_profiles, status=PostStatus.PUBLISHED)\
                .order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Profile.DoesNotExist:
            return Response(error_response("Profile not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LatestPostsAPIView(APIView, PaginationMixin):
    
    def get(self, request):
        try:
            posts = Post.objects.filter(status=PostStatus.PUBLISHED).order_by('-created_at')
            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HashtagPostsView(APIView, PaginationMixin):
    """
    GET /api/hashtags/<hashtag_name>/posts/
    Returns paginated posts under the given hashtag.
    """
    def get(self, request, hashtag_name):
        try:
            hashtag = get_object_or_404(Hashtag, name=hashtag_name.lower())
            posts = hashtag.posts.filter(status=PostStatus.PUBLISHED).order_by('-created_at')

            paginated_queryset = self.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

