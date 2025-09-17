# urls.py
from django.urls import path
from .views import NotificationListView, NotificationMarkReadView, BulkCustomEmailAPIView

urlpatterns = [
    path('user/notifications/', NotificationListView.as_view(), name='notification-list'),
    path("notifications/mark-read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("send-custom-email/", BulkCustomEmailAPIView.as_view(), name="send-custom-email"),
]
