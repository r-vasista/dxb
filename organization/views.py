# Django imports
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers

# Local imports 
from organization.models import (
    Organization, Address
)
from organization.serializers import (
    AddressSerializer, RegisterOrganizationSerializer
)
from organization.utils import (
    generate_otp, verify_otp
)
from organization.services import (
    send_email
)

from user.models import UserType
from user.serializers import UserSerializer


User = get_user_model()

class RegisterOrganizationAPIView(APIView):
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')
        otp = data.get('otp', '')

        if not verify_otp(email, otp):
            return Response({'detail': 'Invalid or expired OTP.'}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({'detail': 'A user with this email already exists.'}, status=400)

        try:
            with transaction.atomic():
                # Get or create user_type
                user_type_obj, _ = UserType.objects.get_or_create(code='organization')

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

                return Response({'detail': 'Organization registered successfully.'}, status=201)

        except ObjectDoesNotExist as e:
            return Response({'detail': f'Missing related object: {str(e)}'}, status=400)
        except serializers.ValidationError as ve:
            return Response(ve.detail, status=400)
        except Exception as e:
            return Response({'detail': f'Unexpected error: {str(e)}'}, status=500)


class SendRegisterOTPIView(APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({'detail': 'Email is required.'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'detail': 'A user with this email already exists.'}, status=400)

        otp = generate_otp(email)
        send_email(
            subject="Your OTP Code",
            text_content=f"Your OTP code is {otp}",
            template_address='organization_register.html',
            context={
                'otp':otp
            },
            to_email_list=[email]
        )
        return Response({"detail": "OTP sent to email."})
