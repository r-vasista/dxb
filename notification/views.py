# views.py
from django.http import Http404
from django.db.models import Q
from django.utils import timezone


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


from collections import defaultdict

from profiles.models import Profile

# from notification.task import send_daily_muse_email_task


from .models import Notification, DailyQuoteSeen

from .serializers import NotificationSerializer
from core.services import error_response, get_user_profile, send_dynamic_email_using_template  # replace with your actual helper
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
        

class BulkCustomEmailAPIView(APIView):
    """
    API for admin to send any stored EmailTemplate to selected profiles.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile_ids = request.data.get("profile_ids", [])
        template_name = request.data.get("template_name")
        context = request.data.get("context", {})

        if not profile_ids or not isinstance(profile_ids, list):
            return Response({"error": "profile_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        if not template_name:
            return Response({"error": "template_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        sent_emails = []
        skipped = []

        profiles = Profile.objects.filter(
            id__in=profile_ids,
            notify_email=True
        ).filter(
            Q(user__email__isnull=False) & ~Q(user__email="")
        ).select_related("user")

        for profile in profiles:
            try:
                send_dynamic_email_using_template(
                    template_name= template_name,
                    recipient_list=[profile.user.email],
                    context={
                        "user_name": profile.username,
                        **context
                    }
                )
                sent_emails.append(profile.user.email)
            except Exception as e:
                skipped.append({"id": profile.id, "username": profile.username, "reason": str(e)})

        return Response({
            "template": template_name,
            "sent_count": len(sent_emails),
            "sent_emails": sent_emails,
            "skipped_count": len(skipped),
            "skipped": skipped
        }, status=status.HTTP_200_OK)