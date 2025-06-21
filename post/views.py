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
from core.services import success_response, error_response
from core.pagination import PaginationMixin
from profiles.models import (
    Profile
)
from post.models import (
    Post, PostMedia
)
from post.serializers import (
    PostSerializer, ImageMediaSerializer
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
            serializer = PostSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            post = serializer.save(profile=profile, created_by=request.user)

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

            serializer = PostSerializer(post, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
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
            serializer = PostSerializer(post)
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
            serializer = PostSerializer(paginated_queryset, many=True)

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
            serializer = PostSerializer(paginated_queryset, many=True)

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
