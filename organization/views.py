# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# Local imports 
from organization.models import (
    OrganizationType, IndustryType, Organization, OrganizationProfileField
)
from organization.serializers import (
    AddressSerializer, RegisterOrganizationSerializer, OrganizationTypeSerializer, IndustryTypeSerializer, OrganizationProfileFieldSerializer,
    UpdateOrganizationProfileFieldSerializer
)
from organization.utils import (
    generate_otp, verify_otp
)
from organization.services import (
    send_register_otp_to_email
)
from user.permissions import (
    HasPermission
)

from user.models import UserType
from user.serializers import UserSerializer

from core.services import success_response, error_response


User = get_user_model()

class RegisterOrganizationAPIView(APIView):
    """
    API endpoint to register a new organization.

    This view performs the following actions:
    - Verifies the OTP sent to the provided email.
    - Creates a user with 'organization' user type.
    - Creates an address record.
    - Creates an organization profile linked to the user and address.

    Request Body:
    {
        "email": "org@example.com",
        "password": "strongpassword",
        "otp": "123456",
        "name": "Organization Name",
        "phone_number": "+1234567890",
        "website": "https://example.com",
        "organization_type": 1,
        "industry_type": 1,
        "address": {
            "line1": "123 Street",
            "line2": "Apt 4",
            "city": "City",
            "state": "State",
            "zipcode": "123456",
            "country": "Country"
        }
    }

    Responses:
    - 201: Organization registered successfully.
    - 400: Validation error, missing or invalid input.
    - 500: Internal server error.
    """
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')
        otp = data.get('otp', '')

        try:
            if not email:
                raise ValueError('Email is required')

            if not verify_otp(email, otp):
                return Response(error_response('Invalid or expired OTP.'), status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Get or create user_type
                user_type_obj, _ = UserType.objects.get_or_create(
                    code='organization',
                    defaults={
                        "name":"Organization"
                    })

                # Create user
                user_serializer = UserSerializer(data={
                    'email': email,
                    'password': password,
                    'user_type': user_type_obj.id
                })
                user_serializer.is_valid(raise_exception=True)
                user = user_serializer.save()

                # Create address
                address_data = data.get('address', {})
                address_serializer = AddressSerializer(data=address_data)
                address_serializer.is_valid(raise_exception=True)
                address = address_serializer.save()

                # Create organization
                organization_data = {
                    'name': data.get('name'),
                    'email': email,
                    'phone_number': data.get('phone_number'),
                    'website': data.get('website'),
                    'organization_type': data.get('organization_type'),
                    'industry_type': data.get('industry_type'),
                    'address': address.id,
                    'user': user.id
                }

                organization_serializer = RegisterOrganizationSerializer(data=organization_data)
                organization_serializer.is_valid(raise_exception=True)
                organization_serializer.save()

                return Response(success_response('Organization registered successfully.'), status=201)

        except ObjectDoesNotExist as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response({str(e)}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendRegisterOTPIView(APIView):
    """
    API endpoint to send an OTP to an email address for registration verification.

    This view checks whether the email is already registered, and if not,
    sends an OTP to the email for verification during the signup process.

    Request Body:
    {
        "email": "org@example.com"
    }

    Responses:
    - 201: OTP sent successfully.
    - 400: Email is missing or already in use.
    - 500: Failed to send OTP or internal server error.
    """
    def post(self, request):
        try:
            email = request.data.get('email')

            if not email:
                raise ValueError('Email is required.')
            
            if User.objects.filter(email=email).exists():
                raise ValidationError('Account with this email already exists.')

            # Send OTP via SMS
            sent, message = send_register_otp_to_email(email)
            if not sent:
                return Response(error_response(f'Failed to send OTP, {message}'), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(success_response('OTP sent successfully'), status=status.HTTP_201_CREATED)
        except ValueError as e:
                return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationTypeListView(APIView):
    """
    API endpoint to fetch a list of active organization types.

    This view returns a list of organization types that are marked as active in the system.

    Request:
    - GET /api/organization-types/

    Response:
    - 200: List of organization types.
    - 500: Internal server error.
    """
    def get(self, request):
        try:
            org_types = OrganizationType.objects.filter(is_active=True)
            serializer = OrganizationTypeSerializer(org_types, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IndustryTypeListView(APIView):
    """
    API endpoint to fetch a list of active industry types.

    This view returns a list of industry types that are marked as active in the system.

    Request:
    - GET /api/industry-types/

    Response:
    - 200: List of industry types.
    - 500: Internal server error.
    """
    def get(self, request):
        try:
            industries = IndustryType.objects.filter(is_active=True)
            serializer = IndustryTypeSerializer(industries, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationProfileFieldView(APIView):
    """
    POST /api/organizations/{org_id}/profile-fields/
    Create single or multiple profile fields for an organization
    """

    permission_classes = [HasPermission]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    method_permissions = {
        'POST': 'create_org_prof_field',
        'PUT': 'update_org_prof_field',
        'DELETE': 'delete_org_prof_field',
    }

    def post(self, request, org_id):
        try:
            # Verify organization exists
            get_object_or_404(Organization, id=org_id)

            data = request.data
            if not isinstance(data, list):
                data = [data] 

            created_fields = []

            with transaction.atomic():
                for field_data in data:
                    # Make a mutable copy to add org_id and created_by
                    field_data = field_data.copy()
                    field_data['organization'] = org_id
                    field_data['created_by'] = request.user.id

                    serializer = OrganizationProfileFieldSerializer(data=field_data)
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
        
    def get(self, request, org_id):
        try:
            get_object_or_404(Organization, id=org_id)
            fields = OrganizationProfileField.objects.filter(organization_id=org_id)
            serializer = OrganizationProfileFieldSerializer(fields, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, org_id):
        try:
            org = get_object_or_404(Organization, id=org_id)
            data = request.data
            if not isinstance(data, list):
                data = [data]

            updated_fields = []

            with transaction.atomic():
                for item in data:
                    field_id = item.get("id")
                    if not field_id:
                        raise ValidationError("Each update object must include the 'id' field.")

                    instance = get_object_or_404(OrganizationProfileField, id=field_id, organization_id=org_id)
                    serializer = UpdateOrganizationProfileFieldSerializer(instance, data=item, partial=True)
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

    def delete(self, request, org_id):
        try:
            get_object_or_404(Organization, id=org_id)
            ids = request.data.get('ids')
            if not isinstance(ids, list) or not ids:
                raise ValidationError("A non-empty list of 'ids' is required to delete fields.")

            deleted_count, _ = OrganizationProfileField.objects.filter(
                id__in=ids, organization_id=org_id
            ).delete()

            return Response(success_response(f"{deleted_count} field(s) deleted."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
