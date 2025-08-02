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
    Returns grouped notifications with pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            notif_type_filter = request.query_params.get("notification_type")
            unread = request.query_params.get('unread')

            notifications = Notification.objects.filter(recipient=profile)
            if notif_type_filter:
                notifications = notifications.filter(notification_type=notif_type_filter)
            
            if unread == 'true':
                notifications = notifications.filter(is_read=False)

            notifications = notifications.select_related("sender__user", "recipient__user").order_by("-created_at")
            paginated_notifications = self.paginate_queryset(notifications, request)
            
            unread_count =  notifications.filter(is_read=False).count()

            serializer = NotificationSerializer(paginated_notifications, many=True, context={"request": request})
            all_notification_types = [choice[0] for choice in Notification.notification_type.field.choices]

            return self.get_paginated_response({
                "available_notification_types": all_notification_types,
                "unread_count":unread_count,
                "notifications": serializer.data,
            })

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      

class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/mark-read/

    Accepts a list of notification IDs and marks them as read.
    Request body:
    {
        "notification_ids": [1, 2, 3]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            ids = request.data.get("notification_ids", [])

            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                return Response({"error": "Invalid 'notification_ids' format"}, status=400)

            updated = Notification.objects.filter(
                id__in=ids,
                recipient=profile,
                is_read=False
            ).update(is_read=True)

            return Response({
                "message": f"{updated} notification(s) marked as read.",
                "marked_ids": ids
            }, status=200)
        
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)