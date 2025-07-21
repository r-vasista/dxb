# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.db.models import Q, F, Sum
from django.db import IntegrityError

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly

# Python imports
from datetime import datetime
from decimal import Decimal

# Local imports
from notification.task import send_friend_request_notification_task, send_friend_request_response_notification_task
from post.serializers import PostSerializer
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)
from core.services import (
    success_response, error_response, get_user_profile
)
from profiles.models import (
    Profile, ProfileField, FriendRequest, ProfileFieldSection, ProfileCanvas, StaticProfileField, StaticFieldValue, ProfileView,
    ArtService, ArtServiceInquiry
)
from profiles.serializers import (
    ProfileFieldSerializer, UpdateProfileFieldSerializer, ProfileSerializer, UpdateProfileSerializer, FriendRequestSerializer,
    ProfileDetailSerializer, UpdateProfileFieldSectionSerializer, ProfileListSerializer, ProfileCanvasSerializer, 
    StaticFieldInputSerializer, StaticFieldValueSerializer, ArtServiceSerializer, ArtServiceInquirySerializer
)
from profiles.choices import (
    StaticFieldType, VisibilityStatus
)
from notification.utils import (
    create_dynamic_notification
)
from django.contrib.contenttypes.models import ContentType
from notification.models import Notification
from post.models import (
    Post, PostReaction, Comment, SharePost, PostView
)
from post.choices import (
    PostStatus
)
from post.utils import (
    get_profile_from_request
)
from core.permissions import (
    is_owner_or_org_member
)
from core.pagination import PaginationMixin


class ProfileAPIView(APIView):
    """
    GET /api/profiles/<profile_id>/
    PUT /api/profiles/<profile_id>/
    View or update a profile (user or organization) by profile_id.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            serializer = ProfileDetailSerializer(profile, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response({str(e)}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            if profile.user and profile.user != request.user:
                return Response(error_response("You are not allowed to update this profile."), status=status.HTTP_403_FORBIDDEN)

            serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response({str(e)}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileCanvasView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)

            serializer = ProfileCanvasSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(profile=profile, created_by=request.user)

            return Response(success_response(data=serializer.data), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            canvas_images = ProfileCanvas.objects.filter(profile=profile).order_by('display_order')
            serializer = ProfileCanvasSerializer(canvas_images, many=True)
            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            canvas = get_object_or_404(ProfileCanvas, id=pk, profile=profile)
            serializer = ProfileCanvasSerializer(canvas, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            canvas = get_object_or_404(ProfileCanvas, id=pk, profile=profile)
            canvas.delete()
            return Response(success_response("Canvas image deleted successfully."), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileFieldView(APIView):
    """
    POST /api/profiles/{profile_id}/fields/
    GET/PUT/DELETE: Operate on dynamic fields for a profile (user/org).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            section_data = request.data.get('section')
            fields_data = request.data.get('fields', [])

            if not section_data or not isinstance(fields_data, list):
                return Response(error_response("Both 'section' and 'fields' are required."), status=status.HTTP_400_BAD_REQUEST)

            created_fields = []

            with transaction.atomic():
                # Check if section exists for the profile, else create it
                section, created = ProfileFieldSection.objects.get_or_create(
                    profile=profile,
                    title=section_data.get("title"),
                    defaults={
                        "display_order": section_data.get("display_order", 0),
                        "created_by": request.user
                    }
                )

                for field_data in fields_data:
                    field_data = field_data.copy()
                    field_data['profile'] = profile_id
                    field_data['section'] = section.id
                    field_data['created_by'] = request.user.id

                    serializer = ProfileFieldSerializer(data=field_data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    created_fields.append(serializer.data)

            return Response(success_response(created_fields), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, profile_id):
        try:
            get_object_or_404(Profile, id=profile_id)

            is_public = request.query_params.get('is_public', True)
            queryset = ProfileField.objects.filter(profile_id=profile_id, is_public=is_public)

            field_type = request.query_params.get('field_type')
            if field_type:
                queryset = queryset.filter(field_type=field_type)

            queryset = queryset.order_by('display_order')
            serializer = ProfileFieldSerializer(queryset, many=True)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, profile_id):
        try:
            get_object_or_404(Profile, id=profile_id)

            data = request.data
            if not isinstance(data, list):
                data = [data]

            updated_fields = []
            with transaction.atomic():
                for item in data:
                    field_id = item.get("id")
                    if not field_id:
                        raise ValidationError("Each update object must include the 'id' field.")

                    instance = get_object_or_404(ProfileField, id=field_id, profile_id=profile_id)
                    serializer = UpdateProfileFieldSerializer(instance, data=item, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    updated_fields.append(serializer.data)

            return Response(success_response(updated_fields), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, profile_id):
        try:
            get_object_or_404(Profile, id=profile_id)

            ids = request.data.get('ids')
            if not isinstance(ids, list) or not ids:
                raise ValidationError("A non-empty list of 'ids' is required to delete fields.")

            deleted_count, _ = ProfileField.objects.filter(id__in=ids, profile_id=profile_id).delete()
            return Response(success_response(f"{deleted_count} field(s) deleted."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProfileFieldSectionView(APIView):
    """
    PUT /api/profiles/sections/<int:section_id>/
    Updates title, description, or display_order of a profile section.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, section_id):
        try:
            section = get_object_or_404(ProfileFieldSection, id=section_id)
            
            serializer = UpdateProfileFieldSectionSerializer(section, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, section_id):
        try:
            section = get_object_or_404(ProfileFieldSection, id=section_id)
            section.delete()

            return Response(success_response(f"Section '{section.title}' deleted successfully."), status=status.HTTP_200_OK)

        except Http404:
            return Response(error_response("Section not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProfileDetailView(APIView):
    """
    GET /api/profiles/<username>/
    Returns profile data including dynamic fields and organization info.
    """
    permission_classes = [AllowAny]

    def get(self, request, username):
        try:
            profile = get_object_or_404(Profile, username=username.lower())
            serializer = ProfileDetailSerializer(profile, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendFriendRequestView(APIView):
    """
    POST /api/friends/send-request/
    {
        "to_profile_id": <int>
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            from_profile = get_user_profile(request.user)
            to_profile_id = request.data.get('to_profile_id')

            if not to_profile_id:
                return Response(error_response("to_profile_id is required."), status=status.HTTP_404_NOT_FOUND)

            if from_profile.id == int(to_profile_id):
                return Response(error_response("Cannot send friend request to yourself."), status=status.HTTP_404_NOT_FOUND)

            to_profile = get_object_or_404(Profile, id=to_profile_id)

            # Already friends
            if to_profile in from_profile.friends.all():
                return Response(error_response("You are already friends."), status=status.HTTP_404_NOT_FOUND)

            # Friend request already exists in either direction
            if FriendRequest.objects.filter(
                Q(from_profile=from_profile, to_profile=to_profile) |
                Q(from_profile=to_profile, to_profile=from_profile)
            ).exclude(status__in=['rejected', 'cancelled', 'accepted']).exists():
                return Response(error_response("A friend request already exists between these profiles."),status=status.HTTP_404_NOT_FOUND)

            # Create friend request
            friend_request = FriendRequest.objects.create(
                from_profile=from_profile,
                to_profile=to_profile
            )
            try:
                transaction.on_commit(lambda: send_friend_request_notification_task.delay(friend_request.id))
            except:
                pass
            serializer = FriendRequestSerializer(friend_request)
            return Response(success_response(serializer.data),status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancelFriendRequestView(APIView):
    """
    POST /api/friends/cancel-request/
    {
        "request_id": <int>
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            request_id = request.data.get('request_id')

            if not request_id:
                return Response(error_response("request_id is required."), status=status.HTTP_400_BAD_REQUEST)

            friend_request = get_object_or_404(FriendRequest, id=request_id, from_profile=profile)

            if friend_request.status != 'pending':
                return Response(error_response("Only pending friend requests can be cancelled."), status=status.HTTP_400_BAD_REQUEST)

            Notification.objects.filter(
                sender=friend_request.from_profile,
                recipient=friend_request.to_profile,
                notification_type='friend_request',
                content_type=ContentType.objects.get_for_model(friend_request),
                object_id=friend_request.id
            ).delete()

            friend_request.delete()

            return Response(success_response("Friend request cancelled."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RespondFriendRequestView(APIView):
    """
    POST /api/friends/respond-request/
    {
        "request_id": <int>,
        "action": "accept" | "reject"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            request_id = request.data.get('request_id')
            action = request.data.get('action')

            if not request_id:
                return Response(error_response("request_id is required."), status=status.HTTP_404_NOT_FOUND)

            if action not in ['accept', 'reject']:
                return Response(error_response("Invalid action. Must be 'accept' or 'reject'."), status=status.HTTP_404_NOT_FOUND)

            friend_request = get_object_or_404(FriendRequest, id=request_id, to_profile=profile)

            if friend_request.status != 'pending':
                return Response(error_response("Friend request is not pending."), status=status.HTTP_404_NOT_FOUND)

            if action == 'accept':
                friend_request.status = 'accepted'
                friend_request.save()

                # Establish friendship (symmetrical)
                from_profile = friend_request.from_profile
                to_profile = friend_request.to_profile

                from_profile.friends.add(to_profile)
                to_profile.friends.add(from_profile)
                try:
                    transaction.on_commit(lambda: send_friend_request_response_notification_task.delay(
                        friend_request.id, "accepted"
                    ))
                except:
                    pass
                return Response(success_response("Friend request accepted."), status=status.HTTP_200_OK)

            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                return Response(success_response("Friend request rejected."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveFriendView(APIView):
    """
    POST /api/friends/remove/
    {
        "friend_profile_id": <int>
    }

    Removes a friend (mutually) from the current profile.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            friend_profile_id = request.data.get("friend_profile_id")

            if not friend_profile_id:
                return Response(error_response("friend_profile_id is required."), status=status.HTTP_400_BAD_REQUEST)

            friend_profile = get_object_or_404(Profile, id=friend_profile_id)

            if friend_profile == profile:
                return Response(error_response("You cannot remove yourself as a friend."), status=status.HTTP_400_BAD_REQUEST)

            if friend_profile not in profile.friends.all():
                return Response(error_response("The specified profile is not your friend."), status=status.HTTP_400_BAD_REQUEST)

            # Remove friendship symmetrically
            profile.friends.remove(friend_profile)
            friend_profile.friends.remove(profile)

            return Response(success_response("Friend removed successfully."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class PendingFriendRequestsView(APIView, PaginationMixin):
    """
    GET /api/friends/pending-requests/

    Lists all friend requests where the current user's profile is the receiver (to_profile)
    and the request status is 'pending'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            pending_requests = FriendRequest.objects.filter(
                to_profile=profile,
                status='pending'
            ).select_related('from_profile')
            
            paginated_queryset = self.paginate_queryset(pending_requests, request)
            serializer = FriendRequestSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class FollowProfileView(APIView):
    """
    POST /api/follow/
    {
        "profile_id": <int>
    }

    Authenticated user's profile will follow the given profile.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            current_profile = get_user_profile(request.user)
            target_profile_id = request.data.get('profile_id')

            if not target_profile_id:
                return Response(error_response("profile_id is required."), status=status.HTTP_400_BAD_REQUEST)

            target_profile = get_object_or_404(Profile, id=target_profile_id)

            if current_profile == target_profile:
                return Response(error_response("You cannot follow yourself."), status=status.HTTP_400_BAD_REQUEST)
            
            if target_profile.visibility_status == VisibilityStatus.PRIVATE:
                return Response(error_response("This account is private"), status=status.HTTP_403_FORBIDDEN)

            if target_profile in current_profile.following.all():
                return Response(error_response("You are already following this profile."), status=status.HTTP_400_BAD_REQUEST)

            current_profile.following.add(target_profile)
            try:
                create_dynamic_notification(
                    'follow',
                    {'sender': current_profile, 'target': target_profile}
                )
            except:
                pass
            return Response(success_response("Profile followed successfully."), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnfollowProfileView(APIView):
    """
    POST /api/unfollow/
    {
        "profile_id": <int>
    }

    Authenticated user's profile will unfollow the given profile.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            current_profile = get_user_profile(request.user)
            target_profile_id = request.data.get('profile_id')

            if not target_profile_id:
                return Response(error_response("profile_id is required."), status=status.HTTP_400_BAD_REQUEST)

            target_profile = get_object_or_404(Profile, id=target_profile_id)

            if current_profile == target_profile:
                return Response(error_response("You cannot unfollow yourself."), status=status.HTTP_400_BAD_REQUEST)

            if target_profile not in current_profile.following.all():
                return Response(error_response("You are not following this profile."), status=status.HTTP_400_BAD_REQUEST)

            current_profile.following.remove(target_profile)
            Notification.objects.filter(
                sender=current_profile,
                recipient=target_profile,
                notification_type='follow'
            ).delete()

            return Response(success_response("Profile unfollowed successfully."), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListFriendsView(APIView):
    """
    GET /api/profile/<int:profile_id>/friends/

    Returns all friends of the given profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id=None, username=None):
        try:
            profile = get_profile_from_request(profile_id, username)

            friends = profile.friends.all().order_by('username')
            serializer = ProfileListSerializer(friends, many=True)

            return Response(success_response( data=serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ListFollowersView(APIView, PaginationMixin):
    """
    GET /api/profile/<int:profile_id>/followers/

    Returns all followers of the given profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            followers = profile.followers.all().order_by('username')
            
            paginated_queryset = self.paginate_queryset(followers, request)
            
            serializer = ProfileListSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            

            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListFollowingView(APIView, PaginationMixin):
    """
    GET /api/profile/<int:profile_id>/following/

    Returns all profiles that the given profile is following.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            following = profile.following.all().order_by('username')
            paginated_queryset = self.paginate_queryset(following, request)
            
            serializer = ProfileListSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StaticFieldValueView(APIView):
    """
    POST /api/profiles/static-fields/
    Stores or updates static profile field values for a given profile.
    Supports both regular field values and file uploads in a single API.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)

            field_data = request.data.get("fields")
            if isinstance(field_data, str):
                import json
                field_data = json.loads(field_data)

            serializer = StaticFieldInputSerializer(data=field_data, many=True)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                for item in serializer.validated_data:
                    static_field = item['static_field']
                    field_value = item.get("field_value", "")
                    
                    value_obj, created = StaticFieldValue.objects.get_or_create(
                        profile=profile,
                        static_field=static_field
                    )
                    
                    # Handle file uploads first (check if file is provided for this field)
                    file_key = f"file_{static_field.id}"
                    if file_key in request.FILES:
                        file_data = request.FILES[file_key]
                        
                        # Check if field type supports file uploads
                        if static_field.field_type not in [StaticFieldType.IMAGE, StaticFieldType.FILE]:
                            raise ValueError(f"Field '{static_field.field_name}' does not support file uploads.")
                        
                        value_obj.set_value(file_data)
                    
                    # Handle other field types
                    elif static_field.field_type == StaticFieldType.DATE and field_value:
                        value_obj.set_value(datetime.strptime(field_value, '%Y-%m-%d').date())
                    elif static_field.field_type == StaticFieldType.NUMBER and field_value:
                        value_obj.set_value(Decimal(field_value))
                    elif static_field.field_type == StaticFieldType.BOOLEAN and field_value:
                        bool_value = field_value.lower() in ['true', '1']
                        value_obj.set_value(bool_value)
                    else:
                        value_obj.set_value(field_value)
                    
                    value_obj.save()

            return Response(success_response("Static field data saved."), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """
        GET /api/profiles/static-fields/
        Retrieves static profile field values for the authenticated user's profile.
        """
        try:
            profile = get_user_profile(request.user)
            
            # Get all static field values for this profile
            static_values = StaticFieldValue.objects.filter(
                profile=profile
            ).select_related('static_field', 'static_field__section').order_by(
                'static_field__section__display_order', 
                'static_field__display_order'
            )
            
            serializer = StaticFieldValueSerializer(static_values, many=True)
            return Response(success_response("Static field data retrieved.", serializer.data), 
                          status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
class SearchProfilesAPIView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            query = request.query_params.get('name', '').strip()

            qs = Profile.objects.filter(
                Q(username__icontains=query) |
                Q(bio__icontains=query) |
                Q(tools__icontains=query) |
                Q(awards__icontains=query)
            ).distinct().order_by('id') 

            user = request.user
            if user.is_authenticated and hasattr(user, 'profile'):
                qs = qs.exclude(id=user.profile.id)

            paginated_qs = self.paginate_queryset(qs, request)
            serializer = ProfileSerializer(paginated_qs, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=500)
        
        
class InspiredByFromProfileView(APIView):
    """
    GET /api/profiles/{profile_id}/inspired-by/

    Suggest profiles based on hashtags from top-performing posts of the given profile.
    """
    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            allowed = is_owner_or_org_member(profile=profile, user=request.user)

            if not allowed:
                return Response(error_response("Permission denied."), status=status.HTTP_403_FORBIDDEN)

            # Step 1: Get top 5 most engaged posts of this profile
            top_posts = Post.objects.filter(
                profile=profile,
                status=PostStatus.PUBLISHED
            ).annotate(
                engagement=F('reaction_count') + F('comment_count') + F('view_count')
            ).order_by('-engagement')[:5]

            # Step 2: Collect all hashtags used in those posts
            tag_ids = top_posts.values_list('hashtags', flat=True)
            tag_ids = list(set(tag_ids))  # Remove duplicates

            if not tag_ids:
                return Response(success_response({"profiles": []}))

            # Step 3: Find other posts with those hashtags (exclude self)
            related_posts = Post.objects.filter(
                hashtags__in=tag_ids,
                status=PostStatus.PUBLISHED
            ).exclude(profile=profile).annotate(
                engagement=F('reaction_count') + F('comment_count') + F('view_count')
            )

            # Step 4: Group by profile, sum engagement, get top
            exclude_ids = set()
            exclude_ids.add(profile.id)
            exclude_ids.update(profile.friends.values_list('id', flat=True))
            exclude_ids.update(profile.following.values_list('id', flat=True))

            # Step 5: Group by profile, sum engagement, get top
            top_profiles = (
                related_posts.exclude(profile_id__in=exclude_ids)
                .values('profile')
                .annotate(total_engagement=Sum('engagement'))
                .order_by('-total_engagement')[:10]
            )

            profile_ids = [entry['profile'] for entry in top_profiles]
            profiles = Profile.objects.filter(id__in=profile_ids)

            serializer = ProfileSerializer(profiles, many=True, context={'request': request})
            return Response(success_response({"profiles": serializer.data}))

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateProfileViewAPIView(APIView):
    """
    POST /api/profiles/<profile_id>/view/

    Tracks a view to a profile and increments view_count.
    Accepts both authenticated and anonymous users.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            viewer = request.user if request.user.is_authenticated else None
            viewer_profile = get_user_profile(viewer)

            # Prevent self-views from being tracked
            if viewer and profile == viewer_profile:
                return Response(success_response("Self view ignored"), status=200)

            # Save view
            ProfileView.objects.create(profile=profile, viewer=viewer_profile)

            # Increment view count (denormalized for performance)
            profile.view_count = profile.view_count + 1
            profile.save(update_fields=["view_count"])

            return Response(success_response("Profile view tracked"), status=201)
        
        except IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
                return Response(success_response("Post view tracked already"), status=201)
        except Exception as e:
            return Response(error_response(str(e)), status=500)


class ProfileStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            # Posts created by the user
            posts_created = Post.objects.filter(profile=profile).count()

            # Likes received on posts
            likes_received = PostReaction.objects.filter(post__profile=profile).count()

            # Likes given by the user
            likes_given = PostReaction.objects.filter(profile=profile).count()

            # Comments made by the user
            comments_made = Comment.objects.filter(profile=profile).count()

            # Comments received on user's posts
            comments_received = Comment.objects.filter(post__profile=profile).count()

            # Shares made by the user
            shares = SharePost.objects.filter(profile=profile).count()

            # Followers / Following / Friends
            followers_count = profile.followers.count()
            following_count = profile.following.count()
            friends_count = profile.friends.count()

            # Profile views
            profile_views = ProfileView.objects.filter(profile=profile).count()

            # Post views
            post_views = PostView.objects.filter(post__profile=profile).count()

            return Response({
                "posts_created": posts_created,
                "likes_received": likes_received,
                "likes_given": likes_given,
                "comments_made": comments_made,
                "comments_received": comments_received,
                "shares": shares,
                "followers": followers_count,
                "following": following_count,
                "friends": friends_count,
                "profile_views": profile_views,
                "post_views": post_views,
            })
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RecentlyInteractedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)
        interaction_type = request.query_params.get('type')

        data = {}

        # Recently liked posts
        if not interaction_type or interaction_type == 'liked':
            liked_post_ids = (
                PostReaction.objects
                .filter(profile=profile)
                .order_by('-created_at')
                .values_list('post_id', flat=True)[:20]
            )
            liked_posts = Post.objects.filter(id__in=liked_post_ids)
            data['liked_posts'] = PostSerializer(liked_posts, many=True, context={'request': request}).data

        # Recently commented posts
        if not interaction_type or interaction_type == 'commented':
            commented_post_ids = (
                Comment.objects
                .filter(profile=profile)
                .order_by('-created_at')
                .values_list('post_id', flat=True)[:20]
            )
            commented_posts = Post.objects.filter(id__in=commented_post_ids)
            data['commented_posts'] = PostSerializer(commented_posts, many=True, context={'request': request}).data

        # Recently shared posts
        if not interaction_type or interaction_type == 'shared':
            shared_post_ids = (
                SharePost.objects
                .filter(profile=profile)
                .order_by('-created_at')
                .values_list('post_id', flat=True)[:20]
            )
            shared_posts = Post.objects.filter(id__in=shared_post_ids)
            data['shared_posts'] = PostSerializer(shared_posts, many=True, context={'request': request}).data

        # Recently viewed posts
        if not interaction_type or interaction_type == 'viewed':
            viewed_post_ids = (
                PostView.objects
                .filter(viewer=profile)
                .order_by('-viewed_at')
                .values_list('post_id', flat=True)[:20]
            )
            viewed_posts = Post.objects.filter(id__in=viewed_post_ids)
            data['viewed_posts'] = PostSerializer(viewed_posts, many=True, context={'request': request}).data

        return Response(data)


class EnableOrUpdateArtServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            
            is_allowed = is_owner_or_org_member(profile=profile, user=request.user)
            if not is_allowed:
                return Response(error_response('You are not allowed to perform this action'), status=status.HTTP_403_FORBIDDEN)

            serializer = ArtServiceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            art_service, created = ArtService.objects.update_or_create(
                profile=profile,
                defaults=serializer.validated_data
            )

            # Enable art service on profile
            profile.art_service_enabled = True
            profile.save(update_fields=["art_service_enabled"])

            return Response(success_response("Art service enabled successfully."), status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:return Response({"status": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetArtServiceAPIView(APIView):
    """
    GET /api/art-service/?profile_id=<id> OR ?username=<username>
    Returns art service details for the given profile.
    """
    def get(self, request):
        try:
            profile_id = request.query_params.get('profile_id')
            username = request.query_params.get('username')

            if not profile_id and not username:
                return Response(error_response("Provide either profile_id or username"), status=status.HTTP_400_BAD_REQUEST)

            profile = None
            if profile_id:
                profile = get_object_or_404(Profile, id=profile_id)
            elif username:
                profile = get_object_or_404(Profile, username=username)

            if not profile.art_service_enabled:
                return Response(error_response("This artist has not enabled art services."), status=status.HTTP_404_NOT_FOUND)

            art_service = get_object_or_404(ArtService, profile=profile)
            serializer = ArtServiceSerializer(art_service)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendArtServiceInquiryAPIView(APIView):
    """
    POST /api/art-service/inquire/
    Authenticated users can send an inquiry to an artist.
    Request data:
    {
        "artist_profile_id": 5,
        "message": "I would like to commission a painting."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            artist_profile_id = request.data.get("artist_profile_id")
            message = request.data.get("message", "").strip()

            if not artist_profile_id:
                return Response(error_response("artist_profile_id is required."), status=status.HTTP_400_BAD_REQUEST)

            artist_profile = get_object_or_404(Profile, id=artist_profile_id)
            inquirer_profile = get_user_profile(request.user)

            if artist_profile == inquirer_profile:
                return Response(error_response("You cannot send an inquiry to yourself."), status=status.HTTP_400_BAD_REQUEST)
            
            if not artist_profile.art_service_enabled:
                return Response(error_response("This artist has not enabled art services."),status=status.HTTP_403_FORBIDDEN)

            # Prevent duplicate inquiries
            inquiry, created = ArtServiceInquiry.objects.get_or_create(
                artist_profile=artist_profile,
                inquirer_profile=inquirer_profile,
                defaults={"message": message}
            )

            if not created:
                return Response(success_response("You have already sent an inquiry to this artist."), status=status.HTTP_200_OK)

            serializer = ArtServiceInquirySerializer(inquiry)
            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ArtServiceInquiriesAPIView(APIView):
    """
    GET /api/art-service/inquiries/
    Returns:
    - Inquiries sent by the logged-in user (as inquirer)
    - Inquiries received by the logged-in user (as artist)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            is_allowed = is_owner_or_org_member(profile=profile, user=request.user)
            if not is_allowed:
                return Response(error_response('You are not allowed to perform this action'), status=status.HTTP_403_FORBIDDEN)

            sent_inquiries = ArtServiceInquiry.objects.filter(
                inquirer_profile=profile
            ).select_related('artist_profile').order_by('-created_at')

            received_inquiries = ArtServiceInquiry.objects.filter(
                artist_profile=profile
            ).select_related('inquirer_profile').order_by('-created_at')

            sent_serializer = ArtServiceInquirySerializer(sent_inquiries, many=True)
            received_serializer = ArtServiceInquirySerializer(received_inquiries, many=True)

            return Response(success_response({
                "sent": sent_serializer.data,
                "received": received_serializer.data
            }), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SuggestedProfilesAPIView(APIView, PaginationMixin):
    """
    GET /api/profiles/suggested/
    Returns a paginated list of 10 verified profiles (excluding the current user).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            # Base queryset: Verified profiles excluding self
            suggestions = Profile.objects.filter(is_verified=True).exclude(id=profile.id)

            # Apply pagination
            paginated_qs = self.paginate_queryset(suggestions, request)
            serializer = ProfileSerializer(paginated_qs, many=True, context={'request': request})

            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)