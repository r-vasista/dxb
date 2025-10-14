# Django imports
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import Http404

from datetime import timedelta

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly

# Local imports
from core.services import (
    success_response, error_response, get_user_profile
)
from subscription.models import (
    SubscriptionPlan, UserSubscription
)
from payment.serializers import (
    TransactionModelSerializer
)
from payment.main import (
    RazorpayClient
)
from payment.models import (
    PaymentTransaction
)
from payment.utils import (
    convert_currency
)

rz_client = RazorpayClient()

class CreateRazorpayOrderAPIView(APIView):
    """
    POST /api/subscription/create-order/
    
    Creates a Razorpay order for the selected plan.

    **Payload Example:**
    {
        "plan_id": 3,
        "currency": "USD"
    }

    **Response Example:**
    {
        "success": true,
        "data": {
            "order_id": "order_JvP4gLhP3FZs9u",
            "amount": 49900,
            "currency": "USD",
            "plan_name": "Gold Membership"
        }
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            plan_id = request.data.get("plan_id")
            currency = request.data.get("currency", "USD").upper()

            plan = get_object_or_404(SubscriptionPlan, id=plan_id)

            # Convert currency (raise error if fails)
            converted_amount = convert_currency(plan.price, plan.currency, currency)
            if not converted_amount:
                raise ValidationError("Currency conversion failed. Please try again later.")

            # Handle smallest unit conversion
            no_fraction_currencies = ["JPY", "KRW", "VND"]
            if currency.upper() in no_fraction_currencies:
                smallest_unit_amount = int(converted_amount)
            else:
                smallest_unit_amount = int(converted_amount * 100)

            # Then create order
            order = rz_client.create_order(
                amount=smallest_unit_amount,
                currency=currency,
                payment_capture=1
            )

            # Save order in DB (optional, before payment)
            PaymentTransaction.objects.create(
                profile=profile,
                plan=plan,
                razorpay_order_id=order["id"],
                amount=converted_amount,
                currency=currency,
                status="CREATED"
            )

            return Response(
                success_response(
                    data={
                        "order_id": order["id"],
                        "amount": converted_amount,
                        "currency": currency,
                        "plan": plan.name
                    },
                    message="Order created successfully."
                ),
                status=status.HTTP_201_CREATED
            )

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class TransactionAPIView(APIView):
    """
    POST /api/subscription/transaction/
    
    Completes an order, verifies the Razorpay payment signature,
    and activates the user’s subscription if successful.
    
    **Payload Example:**
    {
        "plan_id": 3,
        "order_id": "order_JvP4gLhP3FZs9u",
        "payment_id": "pay_JvP7xLxM4pHr3d",
        "signature": "5eaa97b6543a8f...",
        "amount": 499.00,
        "currency": "USD"
    }

    **Response Example:**
    {
        "status": true,
        "message": "Transaction successful and subscription activated.",
        "data": {
            "plan": "Gold Membership",
            "valid_till": "2026-10-14T12:30:00Z"
        }
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            serializer = TransactionModelSerializer(data=request.data, context={'profile': profile})
            serializer.is_valid(raise_exception=True)

            order_id = serializer.validated_data.get("order_id")
            payment_id = serializer.validated_data.get("payment_id")
            signature = serializer.validated_data.get("signature")

            # Verify Razorpay signature
            rz_client.verify_payment_signature(
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature
            )

            # Save transaction
            transaction = serializer.save()

            # Activate subscription
            plan = transaction.plan
            subscription, _ = UserSubscription.objects.get_or_create(profile=profile)
            subscription.plan = plan
            subscription.start_date = timezone.now()
            subscription.end_date = timezone.now() + timedelta(days=plan.duration_days)
            subscription.is_active = True
            subscription.save()

            return Response(
                success_response(
                    data={
                        "plan": plan.name,
                        "valid_till": subscription.end_date
                    },
                    message="Transaction successful and subscription activated."
                ),
                status=status.HTTP_201_CREATED
            )

        except ValidationError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist:
            return Response(error_response("Invalid plan_id."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
