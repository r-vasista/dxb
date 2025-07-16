# views.py
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


from collections import defaultdict

# from notification.task import send_daily_muse_email_task


from .models import Notification, DailyQuoteSeen
from django.utils import timezone
from .serializers import NotificationSerializer
from core.services import error_response, get_user_profile  # replace with your actual helper
from core.pagination import PaginationMixin

class NotificationListView(APIView, PaginationMixin):
    """
    GET /api/notifications/?notification_type=<optional>

    Returns grouped notifications.
    Returns all notification types as metadata.
    Allows filtering by notification type.
    Marks unread notifications as read when accessed.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            # Optional query param filter
            notif_type_filter = request.query_params.get("notification_type")

            notifications = Notification.objects.filter(recipient=profile)
            if notif_type_filter:
                notifications = notifications.filter(notification_type=notif_type_filter)

            notifications = notifications.select_related("sender__user", "recipient__user").order_by("-created_at")
            # Mark unread as read
            notifications.filter(is_read=False).update(is_read=True)
            # Paginate
            paginated_notifications = self.paginate_queryset(notifications, request)

            serializer = NotificationSerializer(paginated_notifications, many=True, context={"request": request})

            # All defined notification types from model
            all_notification_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]

            return self.get_paginated_response({
                "available_notification_types": all_notification_types,
                "notifications": serializer.data
            })
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)