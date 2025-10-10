# chat/views.py
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, F
from django.http import Http404
from django.db import transaction

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser

from core.services import success_response, error_response, get_user_profile
from chat.models import (
    ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt, ChatClear, ChatTheme, ChatGroupTheme, ScheduleMessage
)
from chat.serializers import (
    ChatGroupSerializer, ChatMessageSerializer, ChatGroupMiniSerializer, ScheduleMessageSerializer,
    ChatThemeSerializer
)
from chat.permissions import IsChatMember
from chat.utils import get_or_create_personal_group, is_group_member, broadcast_active_chats_update, can_delete
from chat.choices import ChatType
from chat.tasks import deliver_scheduled_message
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
    Returns paginated messages for a group. (Newest first by default).
    Respects per-user chat clear timestamp.
    """
    permission_classes = [IsAuthenticated, IsChatMember]

    def get(self, request, group_id):
        try:
            group = get_object_or_404(ChatGroup, id=group_id)
            self.check_object_permissions(request, group)

            profile = get_user_profile(request.user)

            before_id = request.query_params.get("before")
            after_id = request.query_params.get("after")

            # Base queryset
            messages = ChatMessage.objects.filter(group=group).exclude(deletions__profile=profile).select_related(
                "sender__user"
            )

            # Apply clear chat filter (skip messages before clear timestamp)
            clear_entry = ChatClear.objects.filter(profile=profile, group=group).first()
            if clear_entry:
                messages = messages.filter(created_at__gt=clear_entry.cleared_at)

            # Apply before/after pagination
            if before_id:
                messages = messages.filter(id__lt=before_id)
            if after_id:
                messages = messages.filter(id__gt=after_id).order_by("id")
            else:
                messages = messages.order_by("-id")

            # Paginate
            page = self.paginate_queryset(messages, request)
            serializer = ChatMessageSerializer(page, many=True, context={"request": request})
            
            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=500)


# class SendMessageAPIView(APIView):
#     """
#     POST /api/chat/groups/<uuid:group_id>/messages/
#     Optional REST endpoint to send a message (WS is primary).
#     """
#     permission_classes = [IsAuthenticated, IsChatMember]

#     def post(self, request, group_id):
#         group = get_object_or_404(ChatGroup, id=group_id)
#         self.check_object_permissions(request, group)

#         profile = get_user_profile(request.user)

#         serializer = ChatMessageSerializer(data=request.data, context={"request": request})
#         if not serializer.is_valid():
#             return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

#         try:
#             with transaction.atomic():
#                 msg = ChatMessage.objects.create(
#                     group=group,
#                     sender=profile,
#                     message_type=serializer.validated_data.get("message_type", ChatMessage.TEXT),
#                     content=serializer.validated_data.get("content", ""),
#                     file=serializer.validated_data.get("file", None),
#                 )
#             out = ChatMessageSerializer(msg, context={"request": request}).data
#             return Response(success_response(out), status=status.HTTP_201_CREATED)
#         except Exception as e:
#             return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

                # Reset unread counter + update last_read_at
                ChatGroupMember.objects.filter(
                    group_id=group_id, profile=profile
                ).update(unread_count=0, last_read_at=now)
                
            # update active chats only for THIS user
            broadcast_active_chats_update(profile.id)

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

                # Find the latest read message
                latest_msg = target_messages.order_by("-created_at").first()

                if latest_msg:
                    ChatGroupMember.objects.filter(
                        group_id=group_id, profile=profile
                    ).update(unread_count=0, last_read_at=now)

            return Response(success_response(
                {"read_count": len(receipts)}, 
                "Selected messages marked as read"
            ))

        except ChatGroup.DoesNotExist:
            return Response(error_response("Chat group not found"), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=500)


class MyActiveChatsAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)
        q = request.query_params.get("q", "").strip()

        qs = (
            ChatGroupMember.objects
            .filter(profile=profile, group__last_message__isnull=False)
            .select_related("group", "group__group", "group__last_message", "group__last_message__sender")
            .order_by("-group__last_message__created_at", "-group__created_at")
        )

        if q:
            qs = qs.filter(
                Q(group__group__name__icontains=q) |
                Q(group__id__icontains=q) |
                Q(group__memberships__profile__username__icontains=q)
            ).distinct()

        page = self.paginate_queryset(qs, request)

        serializer = ChatGroupMiniSerializer(page, many=True, context={"request": request, "profile": profile})
        total_unread_chats = ChatGroupMember.objects.filter(
            profile=profile, unread_count__gt=0, group__last_message__isnull=False
        ).count()

        return self.get_paginated_response({
            "chats": serializer.data,
            "total_unread_chats": total_unread_chats,
        })


class SendMessageAPIView(APIView):
    """
    API for sending a chat message (text, image, or file).
    Triggers a WebSocket broadcast after saving the message.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        profile = get_user_profile(request.user)
        group = ChatGroup.objects.filter(id=group_id).first()
        
        if not group:
            return Response(error_response("Chat group not found"), status=404)

        try:
            with transaction.atomic():
                message_type = request.data.get("message_type", ChatMessage.TEXT)
                content = request.data.get("content", "")
                file = request.FILES.get("file")

                if message_type in [ChatMessage.IMAGE, ChatMessage.FILE] and not file:
                    return Response(error_response("File is required for this message type"), status=400)

                msg = ChatMessage.objects.create(
                    group=group,
                    sender=profile,
                    message_type=message_type,
                    content=content,
                    file=file if file else None,
                )

                # update denormalized fields
                group.last_message = msg
                group.last_message_at = msg.created_at
                group.save(update_fields=["last_message", "last_message_at"])

                # increment unread counts for other members
                ChatGroupMember.objects.filter(group=group).exclude(profile=profile).update(
                    unread_count=F("unread_count") + 1
                )

                # serialize message
                data = ChatMessageSerializer(msg, context={"request": request}).data

                # broadcast message to chat room
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"chat_{group.id}",
                    {"type": "chat.message", "data": data}
                )
                
                # update active chats for all members
                member_ids = ChatGroupMember.objects.filter(group=group).values_list("profile_id", flat=True)
                for pid in member_ids:
                    broadcast_active_chats_update(pid)

            return Response(success_response(data, "Message sent successfully"))

        except Exception as e:
            return Response(error_response(str(e)), status=500)



class DeleteMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        try:
            user = request.user
            profile = get_user_profile(user)
            message = get_object_or_404(ChatMessage, id=message_id)

            # Only sender can delete
            if message.sender != profile:
                return Response(
                    error_response("Not allowed to delete this message"),
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check delete limit and premium invisibility
            ok, invisible_delete = can_delete(profile)
            if not ok:
                return Response(
                    error_response("Daily limit reached! Go Premium to unlock unlimited deletions and exclusive benefits.."),
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            channel_layer = get_channel_layer()
            group = message.group
            last_message_id = group.last_message.id

            if invisible_delete:
                msg_id = message.id
                group = message.group

                # find previous message (non-deleted and older)
                prev_msg = (
                    ChatMessage.objects
                    .filter(group=group)
                    .exclude(id=msg_id)
                    .order_by('-created_at')
                    .first()
                )

                # hard delete the message
                message.delete()

                # update group last_message
                if prev_msg:
                    group.last_message = prev_msg
                    group.last_message_at = prev_msg.created_at
                else:
                    group.last_message = None
                    group.last_message_at = None
                group.save(update_fields=["last_message", "last_message_at"])

                async_to_sync(channel_layer.group_send)(
                    f"chat_{group.id}",
                    {
                        "type": "chat.message_removed",
                        "message_id": str(msg_id),
                        "group_id": str(group.id),
                    },
                )
            else:
                # Free users → soft delete
                message.is_deleted = True
                message.save(update_fields=["is_deleted"])

                async_to_sync(channel_layer.group_send)(
                    f"chat_{group.id}",
                    {
                        "type": "chat.message_deleted",
                        "message_id": str(message.id),
                        "group_id": str(group.id),
                    },
                )

            # Update active chat sidebar if last message was deleted
            if last_message_id == message_id:
                member_ids = list(
                    ChatGroupMember.objects.filter(group=group)
                    .values_list("profile_id", flat=True)
                )
                for pid in member_ids:
                    broadcast_active_chats_update(pid)

            msg = "message deleted" if not invisible_delete else "message permanently deleted"
            return Response(success_response(msg), status=200)

        except Http404 as e:
            return Response(error_response(str(e)), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=500)
        

class ScheduleMessageAPIView(APIView):
    def post(self, request, group_id):
        serializer = ScheduleMessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        scheduled_message = serializer.save(group_id=group_id)

        deliver_scheduled_message.apply_async(
            args=[scheduled_message.id],
            eta=scheduled_message.scheduled_at
        )
        
        return Response(success_response(serializer.data), status=201)


class UploadAndApplyChatThemeAPIView(APIView):
    """
    POST /api/chat/themes/upload-and-apply/

    Allows a user to upload a custom chat theme and apply it to a chat group.
    User must be a member of the given chat group.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            profile = request.user.profile
            group_id = request.data.get("group_id")
            name = request.data.get("name")
            description = request.data.get("description", "")
            background_image = request.data.get("background_image")

            if not group_id or not name:
                return Response(error_response("Both 'group_id' and 'name' are required."), status=400)

            # Validate group and membership
            try:
                group = ChatGroup.objects.get(id=group_id)
            except ChatGroup.DoesNotExist:
                return Response(error_response("Chat group not found."), status=404)

            if not ChatGroupMember.objects.filter(group=group, profile=profile).exists():
                return Response(error_response("You are not a member of this chat group."), status=403)

            with transaction.atomic():
                # Create new custom theme
                theme = ChatTheme.objects.create(
                    name=name,
                    description=description,
                    type="custom",
                    uploaded_by=profile,
                    background_image=background_image,
                    is_public=False,
                )

                # Apply it to the chat
                chat_theme, _ = ChatGroupTheme.objects.update_or_create(
                    group=group,
                    defaults={
                        "theme": theme,
                        "applied_by": profile,
                        "applied_at": timezone.now(),
                    },
                )

            serializer = ChatThemeSerializer(theme)
            return Response(success_response("Theme uploaded and applied successfully.", serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)
        

class RemoveChatThemeAPIView(APIView):
    """
    DELETE /api/chat/themes/remove/

    Removes the applied chat theme from a given chat group.
    User must be a member of the group.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            profile = request.user.profile
            group_id = request.data.get("group_id")

            if not group_id:
                return Response(error_response("'group_id' is required."), status=400)

            # Validate group
            try:
                group = ChatGroup.objects.get(id=group_id)
            except ChatGroup.DoesNotExist:
                return Response(error_response("Chat group not found."), status=404)

            # Check membership
            if not ChatGroupMember.objects.filter(group=group, profile=profile).exists():
                return Response(error_response("You are not a member of this chat group."), status=403)

            # Check if theme exists
            try:
                chat_theme = ChatGroupTheme.objects.get(group=group)
            except ChatGroupTheme.DoesNotExist:
                return Response(error_response("No theme applied to this group."), status=404)

            with transaction.atomic():
                # Remove the theme (but keep record for history if needed)
                chat_theme.delete()

            return Response(success_response("Chat theme removed successfully."), status=200)

        except Exception as e:
            return Response(error_response(str(e)), status=500)


class GetChatThemeAPIView(APIView):
    """
    GET /api/chat/themes/<group_id>/

    Returns the currently applied chat theme for a specific chat group.
    User must be a member of the group.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        try:
            profile = request.user.profile

            # Validate group
            try:
                group = ChatGroup.objects.get(id=group_id)
            except ChatGroup.DoesNotExist:
                return Response(error_response("Chat group not found."), status=404)

            # Check membership
            if not ChatGroupMember.objects.filter(group=group, profile=profile).exists():
                return Response(error_response("You are not a member of this chat group."), status=403)

            # Get current theme
            chat_theme = ChatGroupTheme.objects.filter(group=group).select_related("theme", "applied_by").first()
            if not chat_theme or not chat_theme.theme:
                return Response(success_response("No theme applied for this chat group.", None))

            # Serialize theme
            serializer = ChatThemeSerializer(chat_theme.theme)
            return Response(success_response("Chat theme fetched successfully.", serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)



class GetScheduledMessagesAPIView(APIView, PaginationMixin):
    """
    GET /api/chat/scheduled-messages/?group_id=<id>&executed=true|false&page=1

    Returns all scheduled messages for a group with pagination.
    Allows filtering by executed status.
    User must be a member of the group.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        try:
            profile = request.user.profile
            executed_param = request.query_params.get("executed")

            if not group_id:
                return Response(error_response("'group_id' is required."), status=400)

            # Validate group
            try:
                group = ChatGroup.objects.get(id=group_id)
            except ChatGroup.DoesNotExist:
                return Response(error_response("Chat group not found."), status=404)

            # Check membership
            if not ChatGroupMember.objects.filter(group=group, profile=profile).exists():
                return Response(error_response("You are not a member of this chat group."), status=403)

            # Base queryset
            queryset = ScheduleMessage.objects.filter(group=group).select_related("sender", "group").order_by("-scheduled_at")

            # Apply executed filter
            if executed_param is not None:
                executed_value = executed_param.lower() == "true"
                queryset = queryset.filter(executed=executed_value)

            # Apply pagination
            paginated_qs = self.paginate_queryset(queryset, request)
            serializer = ScheduleMessageSerializer(paginated_qs, many=True)

            # Return paginated response
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=500)
