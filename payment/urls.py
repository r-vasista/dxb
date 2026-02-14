from django.urls import path
from .views import CreateRazorpayOrderAPIView, TransactionAPIView

urlpatterns = [
    path("order/create/", 
        CreateRazorpayOrderAPIView.as_view(), 
        name="razorpay-create-order-api"
    ),
    path("order/complete/", 
        TransactionAPIView.as_view(), 
        name="razorpay-complete-order-api"
    ),
]