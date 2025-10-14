from django.utils import timezone
from rest_framework import serializers

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

        transaction = PaymentTransaction.objects.create(
            profile=profile,
            plan=plan,
            razorpay_order_id=validated_data['order_id'],
            razorpay_payment_id=validated_data['payment_id'],
            razorpay_signature=validated_data['signature'],
            amount=validated_data.get('amount', plan.price),
            currency=validated_data.get('currency', 'INR'),
            status="SUCCESS",
            payment_time=timezone.now(),
        )
        return transaction