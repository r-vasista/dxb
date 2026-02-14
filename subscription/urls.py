from django.urls import path
from subscription.views import SubscriptionListAPIView

urlpatterns = [
    path("subscriptions-list/", SubscriptionListAPIView.as_view(), name="subscription-list"),
]
