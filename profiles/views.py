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
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)
from core.services import (
    success_response, error_response
)
from profiles.models import (
    Profile, ProfileField
)
from profiles.serializers import (
    ProfileFieldSerializer, UpdateProfileFieldSerializer, ProfileSerializer, UpdateProfileSerializer
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
            serializer = ProfileSerializer(profile)
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


class ProfileFieldView(APIView):
    """
    POST /api/profiles/{profile_id}/fields/
    GET/PUT/DELETE: Operate on dynamic fields for a profile (user/org).
    """

    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, profile_id):
        try:
            get_object_or_404(Profile, id=profile_id)

            data = request.data
            if not isinstance(data, list):
                data = [data]

            created_fields = []
            with transaction.atomic():
                for field_data in data:
                    field_data = field_data.copy()
                    field_data['profile'] = profile_id
                    field_data['created_by'] = request.user.id

                    serializer = ProfileFieldSerializer(data=field_data)
                    serializer.is_valid(raise_exception=True)
                    field = serializer.save()
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
        

class ProfileDetailView(APIView):
    """
    GET /api/profiles/<username>/
    Returns profile data including dynamic fields and organization info.
    """
    permission_classes = [AllowAny]

    def get(self, request, username):
        try:
            profile = get_object_or_404(Profile, username=username)
            serializer = ProfileSerializer(profile)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)