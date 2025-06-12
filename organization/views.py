# Django imports
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# Local imports 
from organization.models import (
    OrganizationType, IndustryType, Organization, OrganizationProfileField, OrganizationMember, OrganizationInvite
)
from organization.serializers import (
    AddressSerializer, RegisterOrganizationSerializer, OrganizationTypeSerializer, IndustryTypeSerializer, OrganizationProfileFieldSerializer,
    UpdateOrganizationProfileFieldSerializer, OrganizationInviteSerializer, AcceptInviteSerializer, OrganizationMemberSerializer, 
    OrganizationSerializer
)
from organization.choices import (
    OrgInviteStatus, OrganizationStatus
)
from organization.utils import (
    verify_otp
)
from organization.services import (
    send_register_otp_to_email, send_forgot_otp_to_email
)
from user.permissions import (
    HasPermission, ReadOnly, IsOrgAdminOrMember
)

from user.models import UserType, Role
from user.serializers import UserSerializer, RoleSerializer

from profiles.models import (
    Profile
)
from profiles.choices import (
    ProfileType
)

from core.services import success_response, error_response, send_custom_email


User = get_user_model()


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

    permission_classes = [AllowAny]

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

    permission_classes = [AllowAny]


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

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            industries = IndustryType.objects.filter(is_active=True)
            serializer = IndustryTypeSerializer(industries, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    permission_classes = [AllowAny]

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

                # Assign role to user
                role = Role.objects.get(name='organization')
                user.roles.add(role)

                # Create address
                address_data = data.get('address')
                if address_data:
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
                    'address': address.id if address_data else None,
                    'user': user.id
                }

                organization_serializer = RegisterOrganizationSerializer(data=organization_data)
                organization_serializer.is_valid(raise_exception=True)
                organization = organization_serializer.save()

                profile = Profile.objects.create(organization=organization, profile_type = ProfileType.ORGANIZATION)

                refresh = RefreshToken.for_user(user)
                token_data = {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'profile_type': profile.profile_type,
                    'profile_id': profile.id
                }

                return Response(success_response(token_data), status=status.HTTP_201_CREATED)

        except ObjectDoesNotExist as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response({str(e)}), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class OrganizationDetailAPIView(APIView):
    """
    API for retrieving, updating, or deleting an organization.
    
    - GET: Fetch organization details.
    - PUT: Update organization details.
    - DELETE: Soft-delete (or deactivate) the organization.
    
    URL: /api/organization/<int:pk>/
    """

    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    # method_permissions = {
    #     'PUT': 'update_org',
    #     'DELETE': 'delete_org',
    # }

    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            organization = get_object_or_404(Organization, pk=pk, is_active=True)
            serializer = OrganizationSerializer(organization)
            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            organization = get_object_or_404(Organization, pk=pk, is_active=True)
            
            data = request.data
            org_data = data.copy()
            address_data = org_data.pop('address', None)  # Remove address from main data

            serializer = OrganizationSerializer(organization, data=org_data, partial=True)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                serializer.save()

                # Handle address update if provided
                if address_data:
                    if organization.address:
                        address_serializer = AddressSerializer(organization.address, data=address_data, partial=True)
                        address_serializer.is_valid(raise_exception=True)
                        address_serializer.save()
                    else:
                        # In case no address exists yet
                        address_serializer = AddressSerializer(data=address_data)
                        address_serializer.is_valid(raise_exception=True)
                        address = address_serializer.save()
                        organization.address = address
                        organization.save()

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            organization = get_object_or_404(Organization, pk=pk, is_active=True)
            organization.is_active = False
            organization.status = OrganizationStatus.INACTIVE
            organization.save()
            return Response(success_response("Organization deleted successfully."), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationListAPIView(APIView):
    """
    GET /api/organizations/
    List all active and public organizations with optional filters.

    Query Params:
    - industry_type: ID of IndustryType
    - organization_type: ID of OrganizationType
    - name: partial name match (case-insensitive)

    Returns:
    - 200: List of organizations
    - 500: Internal server error
    """

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            queryset = Organization.objects.filter(
                is_active=True,
                status = OrganizationStatus.ACTIVE
            )

            industry_type = request.query_params.get('industry_type')
            organization_type = request.query_params.get('organization_type')
            name = request.query_params.get('name')

            if industry_type:
                queryset = queryset.filter(industry_type_id=industry_type)

            if organization_type:
                queryset = queryset.filter(organization_type_id=organization_type)

            if name:
                queryset = queryset.filter(name__icontains=name)

            queryset = queryset.order_by('name')
            serializer = OrganizationSerializer(queryset, many=True)
            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationProfileFieldView(APIView):
    """
    POST /api/organizations/{org_id}/profile-fields/
    Create single or multiple profile fields for an organization
    """

    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    # parser_classes = (MultiPartParser, FormParser, JSONParser)
    # method_permissions = {
    #     'POST': 'create_org_prof_field',
    #     'PUT': 'update_org_prof_field',
    #     'DELETE': 'delete_org_prof_field',
    # }

    permission_classes = [AllowAny]

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

            is_public = request.query_params.get('is_public', True)
            queryset  = OrganizationProfileField.objects.filter(organization_id=org_id, is_public=is_public)
            
            field_type = request.query_params.get('field_type') 
            if field_type:
                queryset = queryset.filter(field_type=field_type)
            queryset = queryset.order_by('display_order')

            serializer = OrganizationProfileFieldSerializer(queryset, many=True)
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


class SendInviteAPIView(APIView):
    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    # permission_required = 'create_org_invite'
    permission_classes = [AllowAny]

    def post(self, request, org_id):
        try:
            organization = get_object_or_404(Organization, pk=org_id)

            serializer = OrganizationInviteSerializer(data=request.data, context={'request': request, 'organization': organization})
            serializer.is_valid(raise_exception=True)
            invite = serializer.save(organization=organization)

            accept_url = f"{settings.EMAIL_DOMAIL_URL}/accept-invite/{invite.token}/"
            send_custom_email(
                subject=f"You're invited to join {organization.name}",
                text_content=f"Click here to accept the invite: {accept_url}",
                template_address='org_invite.html',
                context={'invite': invite, 'accept_url': accept_url},
                recipient_list=[invite.email],
            )

            return Response(success_response('Invite sent successfully.'), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListOrganizationInvitesAPIView(APIView):
    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    # permission_required = 'view_org_invite'
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        try:
            organization = get_object_or_404(Organization, pk=org_id)
            invites = OrganizationInvite.objects.filter(organization=organization)

            # Optional filters
            role_id = request.query_params.get('role')
            status_filter = request.query_params.get('status')
            invited_by = request.query_params.get('invited_by')
            expires_after = request.query_params.get('expires_at__gte')

            if role_id:
                invites = invites.filter(role_id=role_id)
            if status_filter:
                invites = invites.filter(status=status_filter)
            if invited_by:
                invites = invites.filter(invited_by_id=invited_by)
            if expires_after:
                try:
                    dt = parse_datetime(expires_after)
                    if dt:
                        invites = invites.filter(expires_at__gte=dt)
                except Exception:
                    return Response(error_response("Invalid 'expires_at__gte' datetime format."), status=status.HTTP_400_BAD_REQUEST)

            invites = invites.order_by('-created_at')
            serializer = OrganizationInviteSerializer(invites, many=True)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcceptInviteAPIView(APIView):
    """
    API to accept an invitation and register a user to an organization.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = AcceptInviteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            invite = serializer.validated_data['token']
            password = serializer.validated_data['password']
            full_name = serializer.validated_data['full_name']

            with transaction.atomic():
                # Get or create 'staff' user_type
                user_type_obj, _ = UserType.objects.get_or_create(
                    code='staff',
                    defaults={"name": "Staff"}
                )

                # Create user
                user_serializer = UserSerializer(data={
                    'email': invite.email,
                    'password': password,
                    'user_type': user_type_obj.id,
                    'full_name':full_name
                })
                user_serializer.is_valid(raise_exception=True)
                user = user_serializer.save()

                # Assign role to user
                user.roles.add(invite.role)

                # Add user to organization via serializer
                member_data = {
                    'organization': invite.organization.id,
                    'user': user.id
                }
                member_serializer = OrganizationMemberSerializer(data=member_data)
                member_serializer.is_valid(raise_exception=True)
                member_serializer.save()

                # Mark the invite as accepted
                invite.status = OrgInviteStatus.ACCEPTED
                invite.save()

                return Response(success_response("Invite accepted and user registered successfully."), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class OrganizationMembersListAPIView(APIView):
    """
    API to list all members of a specific organization.
    """
    # permission_classes = [HasPermission, IsOrgAdminOrMember]
    # permission_required ='view_org_member'
    permission_classes = [AllowAny]

    def get(self, request, org_id):
        try:
            organization = get_object_or_404(Organization, pk=org_id)

            members = OrganizationMember.objects.filter(organization=organization).select_related('user')
            serializer = OrganizationMemberSerializer(members, many=True)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendForgotPasswordOTPIView(APIView):
    """
    POST /api/auth/forgot-password/send-otp/

    Sends an OTP to the email address for password reset.

    Request Body:
    {
        "email": "user@example.com"
    }

    Responses:
    - 201: OTP sent successfully.
    - 400: Email missing or not registered.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                raise ValueError("Email is required.")

            if not User.objects.filter(email=email).exists():
                raise ValidationError("No account found with this email.")

            sent, message = send_forgot_otp_to_email(email)
            if not sent:
                return Response(error_response(f"Failed to send OTP: {message}"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(success_response("OTP sent successfully"), status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordWithOTPAPIView(APIView):
    """
    POST /api/auth/forgot-password/reset/

    Resets the password after verifying OTP.

    Request Body:
    {
        "email": "user@example.com",
        "otp": "123456",
        "new_password": "NewStrongPassword123"
    }

    Responses:
    - 200: Password reset successful.
    - 400: Validation errors or OTP failure.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')
            new_password = request.data.get('new_password')

            if not all([email, otp, new_password]):
                raise ValueError("Email, OTP, and new password are required.")

            if not verify_otp(email, otp):
                return Response(error_response("Invalid or expired OTP."), status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            return Response(success_response("Password has been reset successfully."), status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(error_response("User not found."), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class SendPasswordResetLinkAPIView(APIView):
    """
    POST /api/auth/forgot-password/send-link/

    Sends a password reset link to the registered email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get("email")
            if not email:
                raise ValueError("Email is required.")

            user = User.objects.filter(email=email).first()
            if not user:
                raise ValidationError("No account found with this email.")

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)

            # Frontend URL for resetting password
            reset_url = f"{settings.FRONTEND_URL}/reset-password/?uid={uid}&token={token}"

            subject = "Reset your password"
            text_content = f"Click the link below to reset your password:\n{reset_url}"
            html_template = "password_reset_email.html"
            context = {"reset_url": reset_url}

            status_ok, message = send_custom_email(
                subject=subject,
                text_content=text_content,
                template_address=html_template,
                context=context,
                recipient_list=[email]
            )

            if not status_ok:
                return Response(error_response(f"Failed to send email: {message}"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(success_response("Password reset link sent."), status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordViaLinkAPIView(APIView):
    """
    POST /api/auth/forgot-password/confirm/

    Confirms reset token and updates the password.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            uidb64 = request.data.get("uid")
            token = request.data.get("token")
            new_password = request.data.get("new_password")

            if not all([uidb64, token, new_password]):
                raise ValueError("Missing required fields.")

            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response(error_response("Invalid or expired token."), status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            return Response(success_response("Password reset successful."), status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(error_response("Invalid user."), status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)