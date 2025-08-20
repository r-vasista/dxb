# chat/views.py
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.http import Http404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from core.services import success_response, error_response, get_user_profile
from chat.models import ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt
from chat.serializers import ChatGroupSerializer, ChatMessageSerializer
from chat.permissions import IsChatMember
from chat.utils import get_or_create_personal_group, is_group_member
from chat.choices import ChatType
from profiles.models import Profile
from core.pagination import PaginationMixin


class EnsurePersonalChatAPIView(APIView):
    """
    POST /api/chat/ensure-personal/<int:profile_id>/
    Ensures (creates or returns) a personal chat group between the current user and target profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        my_profile = get_user_profile(request.user)
        other = get_object_or_404(Profile, id=profile_id)

        try:
            group = get_or_create_personal_group(my_profile, other)
            serializer = ChatGroupSerializer(group, context={"request": request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyChatGroupsAPIView(APIView, PaginationMixin):
    """
    GET /api/chat/my-groups/?q=<search>
    Lists all chat groups the current user is in, ordered by recent activity.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)
        q = request.query_params.get("q")

        groups = ChatGroup.objects.filter(
            memberships__profile=profile, type=ChatType.GROUP
        ).order_by("-last_message_at", "-created_at").distinct()

        if q:
            # Search in linked Group name or id
            groups = groups.filter(
                Q(group__name__icontains=q) |
                Q(group__id__icontains=q)
            )

        page = self.paginate_queryset(groups, request)
        serializer = ChatGroupSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


class GroupMessagesAPIView(APIView, PaginationMixin):
    """
    GET /api/chat/groups/<uuid:group_id>/messages/?before=<id>&after=<id>
    Returns paginated messages for a group. (Newest first by default)
    """
    permission_classes = [IsAuthenticated, IsChatMember]

    def get(self, request, group_id):
        try:
            group = get_object_or_404(ChatGroup, id=group_id)
            self.check_object_permissions(request, group)

            before_id = request.query_params.get("before")
            after_id = request.query_params.get("after")

            messages = ChatMessage.objects.filter(group=group, is_deleted=False).select_related(
                "sender__user"
            ).order_by("-id")

            if before_id:
                messages = messages.filter(id__lt=before_id)
            if after_id:
                messages = messages.filter(id__gt=after_id).order_by("id")

            page = self.paginate_queryset(messages, request)
            serializer = ChatMessageSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        except Http404 as e:
            return Response(error_response(str(e)),status=404)
        except Exception as e:
            return Response(error_response(str(e)),status=400)



class SendMessageAPIView(APIView):
    """
    POST /api/chat/groups/<uuid:group_id>/messages/
    Optional REST endpoint to send a message (WS is primary).
    """
    permission_classes = [IsAuthenticated, IsChatMember]

    def post(self, request, group_id):
        group = get_object_or_404(ChatGroup, id=group_id)
        self.check_object_permissions(request, group)

        profile = get_user_profile(request.user)

        serializer = ChatMessageSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                msg = ChatMessage.objects.create(
                    group=group,
                    sender=profile,
                    message_type=serializer.validated_data.get("message_type", ChatMessage.TEXT),
                    content=serializer.validated_data.get("content", ""),
                    file=serializer.validated_data.get("file", None),
                )
            out = ChatMessageSerializer(msg, context={"request": request}).data
            return Response(success_response(out), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkAllMessagesReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        profile = get_user_profile(request.user)
        now = timezone.now()

        try:
            with transaction.atomic():
                # Get unseen messages in this chat (excluding own)
                unseen_messages = ChatMessage.objects.filter(
                    group_id=group_id
                ).exclude(sender=profile).exclude(
                    receipts__user=profile
                )

                receipts = [
                    MessageReceipt(message=msg, user=profile, is_seen=True, seen_at=now)
                    for msg in unseen_messages
                ]
                MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)

                # Update membership last_read_at
                ChatGroupMember.objects.filter(
                    group_id=group_id, profile=profile
                ).update(last_read_at=now)

            return Response(success_response(
                {"read_count": len(receipts)}, 
                "All unread messages marked as read"
            ))

        except ChatGroup.DoesNotExist:
            return Response(error_response("Chat group not found"), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=500)


class MarkMessagesReadByIdAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        profile = get_user_profile(request.user)
        now = timezone.now()
        message_ids = request.data.get("message_ids", [])

        if not isinstance(message_ids, list) or not message_ids:
            return Response(error_response("message_ids must be a non-empty list"), status=400)

        try:
            with transaction.atomic():
                # Get only given messages from this group
                target_messages = ChatMessage.objects.filter(
                    group_id=group_id, id__in=message_ids
                ).exclude(sender=profile).exclude(
                    receipts__user=profile
                )

                receipts = [
                    MessageReceipt(message=msg, user=profile, is_seen=True, seen_at=now)
                    for msg in target_messages
                ]
                MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)

                # Optional: update last_read_at if the latest marked message is newer
                latest_msg = target_messages.order_by("-created_at").first()
                if latest_msg:
                    ChatGroupMember.objects.filter(
                        group_id=group_id, profile=profile
                    ).update(last_read_at=now)

            return Response(success_response(
                {"read_count": len(receipts)}, 
                "Selected messages marked as read"
            ))

        except ChatGroup.DoesNotExist:
            return Response(error_response("Chat group not found"), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=500)
