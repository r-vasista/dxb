from django.utils import timezone
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from .models import PaymentTransaction
from subscription.models import SubscriptionPlan


class RazorpayOrderSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    currency = serializers.CharField()


class TransactionModelSerializer(serializers.ModelSerializer):
    """Serializer for creating and verifying Razorpay transactions."""

    plan_id = serializers.IntegerField(write_only=True)
    order_id = serializers.CharField(write_only=True)
    payment_id = serializers.CharField(write_only=True)
    signature = serializers.CharField(write_only=True)

    class Meta:
        model = PaymentTransaction
        fields = [
            'plan_id', 'order_id', 'payment_id', 'signature',
            'amount', 'currency'
        ]

    def create(self, validated_data):
        profile = self.context['profile']
        plan_id = validated_data.pop('plan_id')
        plan = SubscriptionPlan.objects.get(id=plan_id)
        order_id = validated_data['order_id']

        # Fetch the existing order record
        try:
            transaction = PaymentTransaction.objects.get(
                razorpay_order_id=order_id, 
                profile=profile
            )
        except PaymentTransaction.DoesNotExist:
            raise ValidationError("No transaction found for the given order_id.")

        # Update transaction details
        transaction.razorpay_payment_id = validated_data['payment_id']
        transaction.razorpay_signature = validated_data['signature']
        transaction.amount = validated_data.get('amount', plan.price)
        transaction.currency = validated_data.get('currency', 'INR')
        transaction.status = "SUCCESS"
        transaction.payment_time = timezone.now()
        transaction.plan = plan
        transaction.save()

        return transaction
