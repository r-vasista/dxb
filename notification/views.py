# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


from collections import defaultdict

# from notification.task import send_daily_muse_email_task


from .models import Notification, DailyQuoteSeen
from django.utils import timezone
from .serializers import NotificationSerializer
from core.services import get_user_profile  # replace with your actual helper


class NotificationListView(APIView):
    """
    GET /api/notifications/

    Returns notifications grouped by type.
    Marks all unread notifications as read when accessed.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)

        # Fetch all notifications
        notifications = Notification.objects.filter(recipient=profile).order_by('-created_at')

        # Mark all unread as read in bulk
        unread = notifications.filter(is_read=False)
        unread.update(is_read=True)

        # Group notifications by type
        grouped = defaultdict(list)
        for notif in notifications:
            grouped[notif.notification_type].append(notif)

        # Serialize each group
        response_data = {
            notif_type: NotificationSerializer(notif_list, many=True).data
            for notif_type, notif_list in grouped.items()
        }

        return Response(response_data)

