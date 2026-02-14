from django.contrib import admin
from payment.models import PaymentTransaction

# Register your models here.
@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'plan', 'razorpay_order_id', 'status']
    search_fields = ['id', 'profile', 'plan', 'razorpay_order_id', 'status']
    list_filter = ['id', 'profile', 'plan', 'razorpay_order_id', 'status']
    
