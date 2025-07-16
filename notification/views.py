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
    GET /api/notifications/

    Returns notifications grouped by type.
    Marks all unread notifications as read when accessed.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            notifications = Notification.objects.filter(
                recipient=profile
            ).order_by('-created_at')
            paginated_notifications = self.paginate_queryset(notifications, request)

            unread = notifications.filter(is_read=False)
            unread.update(is_read=True)

            grouped = defaultdict(list)
            for notif in paginated_notifications:
                grouped[notif.notification_type].append(notif)

            grouped_data = {
                notif_type: NotificationSerializer(notif_list, many=True).data
                for notif_type, notif_list in grouped.items()
            }
            return self.get_paginated_response(grouped_data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
