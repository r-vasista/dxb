# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.db.models import Q

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny

# Python imports
from datetime import datetime
from decimal import Decimal

# Local imports
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)
from core.services import (
    success_response, error_response, get_user_profile
)
from profiles.models import (
    Profile, ProfileField, FriendRequest, ProfileFieldSection, ProfileCanvas, StaticProfileField, StaticFieldValue
)
from profiles.serializers import (
    ProfileFieldSerializer, UpdateProfileFieldSerializer, ProfileSerializer, UpdateProfileSerializer, FriendRequestSerializer,
    ProfileDetailSerializer, UpdateProfileFieldSectionSerializer, ProfileListSerializer, ProfileCanvasSerializer, 
    StaticFieldInputSerializer, StaticFieldValueSerializer
)
from profiles.choices import (
    StaticFieldType
)


class ProfileView(APIView):
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
            profile = get_object_or_404(Profile, username=username, context={'request': request})
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
        

class PendingFriendRequestsView(APIView):
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

            serializer = FriendRequestSerializer(pending_requests, many=True)

            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        
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

            if target_profile in current_profile.following.all():
                return Response(error_response("You are already following this profile."), status=status.HTTP_400_BAD_REQUEST)

            current_profile.following.add(target_profile)

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

            return Response(success_response("Profile unfollowed successfully."), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListFriendsView(APIView):
    """
    GET /api/profile/<int:profile_id>/friends/

    Returns all friends of the given profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            friends = profile.friends.all().order_by('username')
            serializer = ProfileListSerializer(friends, many=True)

            return Response(success_response( data=serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ListFollowersView(APIView):
    """
    GET /api/profile/<int:profile_id>/followers/

    Returns all followers of the given profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            followers = profile.followers.all().order_by('username')
            serializer = ProfileListSerializer(followers, many=True)

            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListFollowingView(APIView):
    """
    GET /api/profile/<int:profile_id>/following/

    Returns all profiles that the given profile is following.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)

            following = profile.following.all().order_by('username')
            serializer = ProfileListSerializer(following, many=True)

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

            
class SearchProfilesAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProfileSerializer

    def get_queryset(self):
        query = self.request.query_params.get('name', '')
        qs = Profile.objects.filter(
            Q(username__icontains=query) |
            Q(bio__icontains=query)
        ).distinct()

        # Exclude the request user's profile (if authenticated and has a profile)
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'profile'):
            qs = qs.exclude(id=user.profile.id)

        return qs