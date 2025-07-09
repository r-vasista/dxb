# Rest Framework imports
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# Djano imports
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

# Local imports
from core.services import success_response, error_response
from user.models import Role, Permission, UserType, UserLog
from user.serializers import RoleSerializer, PermissionSerializer, CustomTokenObtainPairSerializer, UserSerializer
from user.choices import PermissionScope
from user.utils import get_client_ip

from organization.serializers import RegisterOrganizationSerializer, AddressSerializer
from organization.utils import (
    verify_otp
)

from profiles.models import (
    Profile
)
from profiles.choices import (
    ProfileType
)

from notification.utils import send_welcome_email

class RegisterAccountAPIView(APIView):
    """
    API to register either an organization or an user user.

    Expected Request Format:
    {
        "user_type": "organization" | "user",
        "email": "user@example.com",
        "password": "strongpassword",
        "otp": "123456",
        "name": "John Doe",
        "phone_number": "+1234567890",
        "website": "https://example.com",
        "organization_type": 1,
        "industry_type": 1,
        "address": { ... }
    }

    Response:
    - 201: Registration successful with JWT token.
    - 400: Bad request or invalid data.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        user_type = data.get("user_type")
        email = data.get("email", "").lower()
        password = data.get("password")
        otp = data.get("otp", "")
        name = data.get("name", "")
        address_data = data.get("address", {})

        # Location data
        timezone_str = data.get("timezone", "UTC")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        ip_address = get_client_ip(request)

        try:
            if not email or not password or not user_type:
                raise ValueError("Email, password, and user_type are required.")

            if not verify_otp(email, otp):
                return Response(error_response("Invalid or expired OTP."), status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                if user_type == "organization":
                    user_type_obj, _ = UserType.objects.get_or_create(code="organization", defaults={"name": "Organization"})
                    user_serializer = UserSerializer(data={
                        "email": email,
                        "password": password,
                        "user_type": user_type_obj.id,
                        "full_name": name,
                        "timezone": timezone_str
                    })
                    user_serializer.is_valid(raise_exception=True)
                    user = user_serializer.save()

                    role, _ = Role.objects.get_or_create(name='organization')
                    user.roles.add(role)

                    address = None
                    if address_data:
                        address_serializer = AddressSerializer(data=address_data)
                        address_serializer.is_valid(raise_exception=True)
                        address = address_serializer.save()

                    organization_data = {
                        "name": data.get("name"),
                        "email": email,
                        "phone_number": data.get("phone_number"),
                        "website": data.get("website"),
                        "organization_type": data.get("organization_type"),
                        "industry_type": data.get("industry_type"),
                        "address": address.id if address else None,
                        "user": user.id
                    }

                    org_serializer = RegisterOrganizationSerializer(data=organization_data)
                    org_serializer.is_valid(raise_exception=True)
                    organization = org_serializer.save()

                    profile = Profile.objects.create(
                        organization=organization,
                        profile_type=ProfileType.ORGANIZATION,
                        username=name,
                        phone_number=data.get("phone_number")
                    )
                    send_welcome_email(profile)

                elif user_type == "user":
                    user_type_obj, _ = UserType.objects.get_or_create(code="user", defaults={"name": "user"})
                    user_serializer = UserSerializer(data={
                        "email": email,
                        "password": password,
                        "user_type": user_type_obj.id,
                        "full_name": name,
                        "timezone": timezone_str
                    })
                    user_serializer.is_valid(raise_exception=True)
                    user = user_serializer.save()

                    role, _ = Role.objects.get_or_create(name='user')
                    user.roles.add(role)

                    profile = Profile.objects.create(
                        user=user,
                        profile_type=ProfileType.USER,
                        username=name,
                        phone_number=data.get("phone_number")
                    )
                    send_welcome_email(profile)
                else:
                    raise ValueError("Invalid user_type. Must be 'organization' or 'user'.")

                # Log user registration as login
                UserLog.objects.create(
                    user=user,
                    ip_address=ip_address,
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone_str
                )

                # Return token
                refresh = RefreshToken.for_user(user)
                token_data = {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "profile_type": profile.profile_type,
                    "profile_id": profile.id
                }

                return Response(success_response(token_data), status=status.HTTP_201_CREATED)

        except ObjectDoesNotExist as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response({str(e)}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            response_data = serializer.validated_data
            
            user = serializer.user

            # Get IP and optional location/timezone from frontend
            ip = get_client_ip(request)
            lat = request.data.get('latitude')
            lon = request.data.get('longitude')
            tz = request.data.get('timezone', user.timezone)  # frontend detected or user default

            UserLog.objects.create(
                user=user,
                ip_address=ip,
                latitude=lat,
                longitude=lon,
                timezone=tz
            )

            return Response(success_response(response_data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_401_UNAUTHORIZED)


class RoleView(APIView):
    def post(self, request):
        try:
            serializer = RoleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        try:
            role_id = request.query_params.get('role_id')
            org_id = request.query_params.get('organization_id')

            if role_id:
                role = get_object_or_404(Role, pk=role_id, organization__isnull=False)
                serializer = RoleSerializer(role)
                return Response(success_response(serializer.data))

            if org_id:
                roles = Role.objects.filter(organization_id=org_id)
                serializer = RoleSerializer(roles, many=True)
                return Response(success_response(serializer.data))

            raise ValidationError("Either 'role_id' or 'organization_id' must be provided.")

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            role = get_object_or_404(Role, pk=pk)
            serializer = RoleSerializer(role, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(success_response(serializer.data))
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GlobalRoleView(APIView):
    def get(self, request):
        try:
            role_id = request.query_params.get('role_id')

            if role_id:
                role = get_object_or_404(Role, pk=role_id, organization__isnull=True)
                serializer = RoleSerializer(role)
                return Response(success_response(serializer.data))

            roles = Role.objects.filter(organization__isnull=True)
            serializer = RoleSerializer(roles, many=True)
            return Response(success_response(serializer.data))

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PermissionListView(APIView):
    """
    GET /api/permissions/
    Get all visible permissions, optionally filtered by scope.
    Query Params:
      - scope: Optional (e.g., 'org', 'admin', etc.)
    """

    def get(self, request):
        try:
            queryset = Permission.objects.filter(
                is_visible=True,
                scope__in=[PermissionScope.ADMIN, PermissionScope.GLOBAL]
                )
            serializer = PermissionSerializer(queryset, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
