# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


from collections import defaultdict


from .models import Notification
from .serializers import NotificationSerializer
from core.services import get_user_profile  # replace with your actual helper

from .utils import get_random_unseen_quote_for_today

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

class DailyMuseQuoteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)
        quote, seen_at, email_already_sent = get_random_unseen_quote_for_today(profile)

        if quote and not email_already_sent:
            return Response({
                "text": quote.text,
                "author": quote.author,
                "seen_at": seen_at,
                "is_today": True
            })

        return Response({}, status=status.HTTP_200_OK)



