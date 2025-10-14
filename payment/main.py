from .import client
from rest_framework.serializers import ValidationError
from rest_framework import status


class RazorpayClient:

    def create_order(self, amount, currency, payment_capture):
        data = {
            "amount": amount * 100,
            "currency": currency,
            "payment_capture":payment_capture
        }
        try:
            self.order = client.order.create(data=data)
            return self.order
        except Exception as e:
            raise ValidationError(e)
    
    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        try:
            self.verify_signature = client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return self.verify_signature
        except Exception as e:
            raise ValidationError(e)
            