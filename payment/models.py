from django.db import models

from core.models import BaseModel
from profiles.models import Profile
from subscription.models import SubscriptionPlan


class PaymentTransaction(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="transactions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, default="CREATED") 
    payment_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
