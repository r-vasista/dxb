# Rest Framework imports
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

# Djano imports
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q

# Local imports
from core.services import success_response, error_response
from user.models import Role, Permission
from user.serializers import RoleSerializer, PermissionSerializer, CustomTokenObtainPairSerializer
from user.choices import PermissionScope

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            response_data = serializer.validated_data
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
