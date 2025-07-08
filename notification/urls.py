# urls.py
from django.urls import path
from .views import NotificationListView,DailyMuseQuoteAPIView

urlpatterns = [
    path('user/notifications/', NotificationListView.as_view(), name='notification-list'),
    path("daily-muse/", DailyMuseQuoteAPIView.as_view(), name="daily-muse"),
]
