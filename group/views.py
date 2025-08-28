# Rest Framework imports
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied

# Djnago imports
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_date
from django.db.models import Count, Q, F

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupJoinRequest, GroupPostFlag , GroupActionLog
)
from group.choices import (
    RoleChoices, JoiningRequestStatus, GroupAction
)
from group.serializers import (
    GroupCreateSerializer, GroupPostSerializer, GroupDetailSerializer, GroupPostCommentSerializer, AddGroupMemberSerializer, GroupMemberSerializer, 
    GroupListSerializer, GroupPostLikeSerializer, GroupPostCommentLikeSerializer, GroupUpdateSerializer, GroupMemberUpdateSerializer, 
    GroupJoinRequestSerializer, GroupPostFlagSerializer, GroupPostFlagListSerializer , GroupActionLogSerializer, 
    GroupSearchSerializer,GroupSuggestionSerializer, BasicGroupDetailSerializer
)
from group.permissions import (
    can_add_members, IsGroupAdminOrModerator, IsGroupAdmin, IsGroupMember
)
from group.utils import (
    can_post_to_group, handle_grouppost_hashtags, log_group_action, increment_group_member_activity
)
from core.pagination import PaginationMixin
from core.utils import (
    extract_and_assign_hashtags
)
from core.services import (
    success_response, error_response, get_user_profile, get_actual_user
)
from core.models import (
    HashTag
)
from profiles.models import Profile
from event.serializers import (
    EventListSerializer
)
from chat.models import (
    ChatGroup, ChatGroupMember
)
from chat.choices import (
    ChatType
)
from group.task import (notify_owner_of_group_comment_like, notify_owner_of_group_post_comment, notify_owner_of_group_post_like,
                         send_group_creation_notifications_task ,send_group_join_notifications_task,notify_group_members_of_new_post
)

        
class GroupCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_user_profile(request.user)
        serializer = GroupCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # 1. Create the group
                group = serializer.save(creator=profile)

                # 2. Add the creator as admin member
                GroupMember.objects.create(
                    profile=profile,
                    group=group,
                    role=RoleChoices.ADMIN,
                    assigned_by=profile,
                )

                # 3. Extract & assign hashtags
                extract_and_assign_hashtags(group.description, group)
                
                # 4. Log the group creation
                log_group_action(group, profile, GroupAction.CREATE, "Group created by user")

                # 5. --- Create ChatGroup for this group ---
                chat_group = ChatGroup.objects.create(
                    type=ChatType.GROUP,
                    group=group
                )

                # 6. Add creator as a chat group member
                ChatGroupMember.objects.create(
                    group=chat_group,
                    profile=profile,
                )

                # 7. Trigger async notifications (outside transaction)
                try:
                    transaction.on_commit(
                        lambda: send_group_creation_notifications_task.delay(group.id, profile.id)
                    )
                except:
                    pass

            return Response(
                success_response(serializer.data, 'Guild created successfully'),
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class GroupUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get_object(self, group_id):
        try:
            group = Group.objects.get(id=group_id)
            self.check_object_permissions(self.request, group)
            return group
        except Group.DoesNotExist:
            return None

    def put(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(error_response("Group not found."), status=status.HTTP_404_NOT_FOUND)

        serializer = GroupUpdateSerializer(group, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                group = serializer.save()
                extract_and_assign_hashtags(group.description, group)
                log_group_action(group, get_user_profile(request.user), GroupAction.UPDATE, "Group updated by user")
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GroupDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get_object(self, group_id):
        try:
            group = Group.objects.get(id=group_id)
            self.check_object_permissions(self.request, group)
            return group
        except Group.DoesNotExist:
            return None
        
    def delete(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(error_response("Group not found."), status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                log_group_action(group, get_user_profile(request.user), GroupAction.DELETE, "Group deleted by user")
                group.delete()
            return Response(success_response({"message": "Group deleted successfully."}), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GroupDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get_object(self, group_id):
        try:
            group = Group.objects.get(id=group_id)
            self.check_object_permissions(self.request, group)
            return group
        except Group.DoesNotExist:
            return None
        
    def delete(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(error_response("Group not found."), status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                log_group_action(group, get_user_profile(request.user), GroupAction.DELETE, "Group deleted by user")
                group.delete()
            return Response(success_response({"message": "Group deleted successfully."}), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, group_id=None, slug=None):
        try:
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(slug=slug)
                
            serializer = GroupDetailSerializer(group, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response(error_response('Group not found'), status=status.HTTP_404_NOT_FOUND)
        

class GroupPostCreateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            profile = get_user_profile(request.user)

            if not can_post_to_group(group, profile):
                return Response(
                    error_response("You do not have permission to post in this group."),
                    status=status.HTTP_403_FORBIDDEN
                )

            data = request.data.copy()
            data['group'] = group.id
            serializer = GroupPostSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            post = serializer.save(profile=profile)
            handle_grouppost_hashtags(post)
            log_group_action(group, profile, GroupAction.POST_CREATE, "Group post created by user", group_post=post)
            increment_group_member_activity(profile, group, points=5)
            try:
                post_id = post.id
                transaction.on_commit(lambda:notify_group_members_of_new_post.delay(post_id))
            except:
                pass
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Group.DoesNotExist:
            return Response(error_response("Group Not Found"), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)                       
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)   
       
        
class GroupListAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)

            posts_qs = GroupPost.objects.select_related('profile').filter(group=group)

            # Optional filter for is_pinned
            is_pinned = request.query_params.get('is_pinned')
            if is_pinned is not None:
                posts_qs = posts_qs.filter(is_pinned=is_pinned.lower() == 'true')

            # Get pinned posts separately
            pinned_qs = posts_qs.filter(is_pinned=True).exclude(pinned_at__lt=timezone.now() - timedelta(days=10)).order_by('-created_at')
            pinned_data = GroupPostSerializer(pinned_qs, many=True, context={'request': request}).data

            # Paginate ALL posts (pinned + normal)
            all_posts_qs = posts_qs.order_by('-is_pinned', '-created_at')
            paginated_posts = self.paginate_queryset(all_posts_qs, request)
            serialized_posts = GroupPostSerializer(paginated_posts, many=True, context={'request': request}).data

            # Get default paginated response and inject pinned
            paginated_response = self.get_paginated_response(serialized_posts)
            paginated_response.data['pinned'] = pinned_data

            return paginated_response

        except Group.DoesNotExist:
            return Response(error_response("Group Not Found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


      

class  GroupPostDetailAPIView(APIView):

    permission_classes =  [IsAuthenticated]
    def get(self, request, post_id = None, slug = None):

        try:
            if post_id:
                post = GroupPost.objects.get(id=post_id)
            elif slug:
                post = GroupPost.objects.get(slug=slug)
            else:
                return Response(error_response('post id or slug must be provided', status=status.HTTP_400_BAD_REQUEST))
            serializer =  GroupPostSerializer(post)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except GroupPost.DoesNotExist:
            return Response(error_response("Group post not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self,request,post_id):
        try:
            post = GroupPost.objects.select_related("group").get(id=post_id)
            profile = get_user_profile(request.user)

            is_author = post.profile == profile
            group_member = GroupMember .objects.filter(group=post.group,
                                profile=profile,is_banned=False).first()
            allowed_roles = [RoleChoices.ADMIN,RoleChoices.MODERATOR]
            is_privileged = group_member and group_member.role in allowed_roles

            if not (is_author or is_privileged):
                return Response(error_response("you do not have permission to delete this post"),status=status.HTTP_403_FORBIDDEN)
            log_group_action(post.group, profile, GroupAction.POST_DELETE, "Group post deleted by user")
            increment_group_member_activity(profile, post.group, points=2)
            post.delete()
            return Response(success_response("Post Was Delted SucessFully"),status=status.HTTP_200_OK)
        except GroupPost.DoesNotExist:
            return Response(error_response("Group Post Does not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)),status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
    def put(self, request, post_id):
        try:
            post = GroupPost.objects.select_related("group").get(id=post_id)
            profile = get_user_profile(request.user)

            # Only allow author or admin/moderator
            is_author = post.profile == profile
            group_member = GroupMember.objects.filter(
                group=post.group, profile=profile, is_banned=False).first()
            allowed_roles = [RoleChoices.ADMIN, RoleChoices.MODERATOR]
            is_privileged = group_member and group_member.role in allowed_roles

            if not (is_author or is_privileged):return Response(error_response("You do not have permission to update this post."),
                    status=status.HTTP_403_FORBIDDEN,)

            data = request.data.copy()
            
            updated = False

            if "content" in data:
                post.content = data["content"]
                updated = True

            if "tags" in data:
                tag_ids = data.getlist("tags") if hasattr(data, "getlist") else data["tags"]
                post.tags.set(tag_ids)
                updated = True
            handle_grouppost_hashtags(post)  # Define this as shown below.
            if "is_pinned" in data:
                if is_privileged:
                    pin_requested = str(data["is_pinned"]).lower() in ["true", "1", "yes"]

                    if pin_requested:
                        if not post.is_pinned or post.is_pin_expired():
                            post.is_pinned = True
                            post.pinned_at = timezone.now()
                            updated = True
                        else:
                            return Response(
                                error_response("Post is already pinned and has not expired."),
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    else:
                        post.is_pinned = False
                        post.pinned_at = None
                        updated = True
                else:
                    return Response(
                        error_response("Only admins/moderators can pin posts."),
                        status=status.HTTP_403_FORBIDDEN,
                    )
            if updated:
                post.save()
            log_group_action(post.group, profile, GroupAction.POST_UPDATE, "Group post updated by user", group_post=post)
            increment_group_member_activity(profile, post.group, points=3)

            serializer = GroupPostSerializer(post)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except GroupPost.DoesNotExist:
            return Response(error_response("Group post not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)       
        

class CreateGroupPostCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            profile = get_user_profile(request.user)
            if not profile:
                return Response(
                    error_response("User profile not found."),
                    status=400
                )

            group_post = get_object_or_404(GroupPost, id=post_id)
            data = request.data.copy()

            # Optional: parent comment handling
            parent_id = data.get("parent")
            parent_comment = None
            if parent_id:
                parent_comment = GroupPostComment.objects.filter(
                    id=parent_id, group_post=group_post, is_active=True
                ).first()
                if not parent_comment:
                    return Response(
                        error_response("Invalid parent comment."),
                        status=400
                    )

            with transaction.atomic():
                # Create comment via serializer
                serializer = GroupPostCommentSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                comment = serializer.save(
                    profile=profile,
                    group_post=group_post,
                    parent=parent_comment  # None if no parent provided
                )

                # Update comments_count only for top-level comments
                if parent_comment is None:
                    total_top_level_comments = GroupPostComment.objects.filter(
                        group_post=group_post,
                        is_active=True,
                        parent__isnull=True
                    ).count()

                    # Atomic update on GroupPost comments_count
                    GroupPost.objects.filter(id=group_post.id).update(comments_count=total_top_level_comments)
                    group_post.refresh_from_db(fields=['comments_count'])
                if group_post.profile != profile:
                    try:
                        transaction.on_commit(lambda:notify_owner_of_group_post_comment.delay(comment.id))
                    except :
                        pass
            return Response(
                success_response(GroupPostCommentSerializer(comment).data),
                status=201
            )

        except Http404 as e:
            return Response(error_response(str(e)),status=404)
        except Exception as e:
            return Response(error_response(str(e)),status=400)
class ParentGroupPostCommentsAPIView(APIView, PaginationMixin):
    """
    List all top-level comments for a group post (paginated).
    """

    def get(self, request, post_id):
        try:
            comments = GroupPostComment.objects.select_related().filter(
                    group_post__id=post_id,
                    is_active=True,
                    parent__isnull=True,
                ).order_by('-created_at')
            paginated_comments = self.paginate_queryset(comments, request)
            serializer = GroupPostCommentSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response((serializer.data))
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChildGroupPostCommentListAPIView(APIView, PaginationMixin):
    """
    List all child comments (replies) for a parent comment on a group post (paginated).
    """

    def get(self, request, post_id, parent_id):
        try:
            # Validate group post exists
            group_post = get_object_or_404(GroupPost, id=post_id)

            # Validate parent comment exists and is associated with the group post
            parent_comment = get_object_or_404(
                GroupPostComment, id=parent_id, group_post=group_post, is_active=True
            )

            # Fetch replies to the parent comment
            replies = GroupPostComment.objects.filter(
                group_post=group_post,
                parent=parent_comment,
                is_active=True
            ).order_by('created_at')

            # Paginate
            paginated_replies = self.paginate_queryset(replies, request)
            serializer = GroupPostCommentSerializer(
                paginated_replies, many=True, context={'request': request}
            )

            return self.get_paginated_response(serializer.data)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GroupAddMemberAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdminOrModerator]
    
    def get_object(self, group_id):
        try:
            group = Group.objects.get(id=group_id)
            self.check_object_permissions(self.request, group)
            return group
        except Group.DoesNotExist:
            return None

    def post(self, request):
        try:
            data = request.data
            
            # 1. Fetch group
            group = self.get_object(data.get('group'))
            if not group:
                return Response(error_response("Group not found."), status=status.HTTP_404_NOT_FOUND)
            
            # 2. Get request user's profile
            acting_profile = get_user_profile(request.user)
            
            with transaction.atomic():                
                # 3. Validate data
                serializer = AddGroupMemberSerializer(data=data, context={'group': group})
                serializer.is_valid(raise_exception=True)
                group_member = serializer.save(assigned_by=acting_profile)

                # 4. Add to chat group
                if hasattr(group, "chat_group"):
                    ChatGroupMember.objects.get_or_create(
                        group=group.chat_group,
                        profile=group_member.profile
                    )
                else:
                    raise ValidationError('chat group not found')

                # 5. Send async notifications
                try:
                    transaction.on_commit(
                        lambda: send_group_join_notifications_task.delay(
                            group.id, group_member.profile.id, action='joined', sender_id=acting_profile.id
                        )
                    )
                except Exception:
                    pass

                # 6. Update group member count
                group.member_count = GroupMember.objects.filter(group=group).count()
                group.save(update_fields=['member_count'])

                # 7. Log action
                log_group_action(
                    group,
                    acting_profile,
                    GroupAction.MEMBER_ADD,
                    "Group member added",
                    group_member=group_member
                )

            return Response(
                success_response({"message": "Member added successfully."}),
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return Response(error_response("This profile is already a member of the group."),status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupMemberDetailAPIView(APIView):
    """
    PUT: Update a member's role in a group (Admin only)
    DELETE: Remove a member from the group (Admin only)
    """

    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get_object(self, group_id):
        try:
            group = Group.objects.get(id=group_id)
            self.check_object_permissions(self.request, group)
            return group
        except Group.DoesNotExist:
            return None
        
    def get(self, request, id):
        """
        Retrieve details of a specific member in the group.
        """
        try:

            group_member = get_object_or_404(GroupMember.objects.select_related('profile', 'group'), id=id)
            serializer = GroupMemberSerializer(group_member)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def put(self, request):
        """
        Update a member's role in the group.
        """
        try:
            group = self.get_object(request.data.get('group'))
            profile = request.data.get('profile')

            member = get_object_or_404(GroupMember, profile=profile, group=group)

            serializer = GroupMemberUpdateSerializer(member, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            group_member=serializer.save()
            log_group_action(group, member.profile, GroupAction.MEMBER_UPDATE, "Group member role updated", group_member=member)
            try:
                transaction.on_commit(lambda: send_group_join_notifications_task.delay(group.id, group_member.profile.id, action='updated',sender_id=get_user_profile(request.user).id))
            except:
                pass

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """
        Remove a member from the group.
        """
        try:
            group = self.get_object(request.data.get('group'))
            member = request.data.get('profile')

            group_member = get_object_or_404(GroupMember, profile=member, group=group)
            
            if group_member.profile == group.creator:
                return Response(error_response('Can not remove the group owner'), status=status.HTTP_403_FORBIDDEN)

            group_member.delete()
            log_group_action(group, member, GroupAction.MEMBER_REMOVE, "Group member role updated")
            group.member_count = GroupMember.objects.filter(group=group).count()
            group.save(update_fields=['member_count'])
            try:
            
                transaction.on_commit(lambda: send_group_join_notifications_task.delay(group.id, group_member.profile.id, action='removed',sender_id=member))
            except: 
                pass

            return Response(success_response("Member removed successfully"), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GroupMemberListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupMember]

    def get(self, request, group_id=None, slug=None):
        try:
            
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(slug=slug)
                
            self.check_object_permissions(self.request, group)

            # Fetch all active members
            members = GroupMember.objects.select_related('profile').filter(group=group)

            serializer = GroupMemberSerializer(members, many=True, context={'request':request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response(error_response("Group not found"), status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NewGroupsListAPIView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            groups = Group.objects.select_related('creator').order_by('-created_at')
            
            paginated_groups = self.paginate_queryset(groups, request)

            serializer = GroupListSerializer(paginated_groups, many=True, context={'request': request})

            return self.get_paginated_response(success_response(serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupPostLikesByIdAPIView(APIView, PaginationMixin):
    """
    GET /groups/posts/<post_id>/likes/
        Returns paginated list of likes on a group post.

    POST
        Toggles like/unlike on a post for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = get_object_or_404(GroupPost, id=post_id)
            likes_qs = GroupPostLike.objects.filter(group_post=post).order_by('-created_at')
            paginated_likes = self.paginate_queryset(likes_qs, request)
            serializer = GroupPostLikeSerializer(paginated_likes, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, post_id):
        try:
            profile = get_user_profile(request.user)
            post = get_object_or_404(GroupPost, id=post_id)
            existing_like = GroupPostLike.objects.filter(group_post=post, profile=profile).first()
            with transaction.atomic():
                if existing_like:
                    existing_like.delete()
                    post.likes_count = F('likes_count') - 1
                    post.save(update_fields=["likes_count"])
                    return Response({"message": "Like removed."}, status=status.HTTP_200_OK)
                else:
                    like = GroupPostLike.objects.create(group_post=post, profile=profile)
                    post.likes_count = F('likes_count') + 1
                    post.save(update_fields=["likes_count"])
                    serializer = GroupPostLikeSerializer(like)
                    try:
                        transaction.on_commit(lambda:notify_owner_of_group_post_like.delay(post.id, profile.id))
                    except:
                        pass
                    return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GroupPostLikeDetailAPIView(APIView):
    """
    GET: Retrieve like detail (only if owned)
    DELETE: Remove like (only if owned)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, profile):
        try:
            return GroupPostLike.objects.get(pk=pk, profile=profile)
        except GroupPostLike.DoesNotExist:
            raise Http404("Like not found or not owned by you.")

    def get(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            like = self.get_object(pk, profile)
            serializer = GroupPostLikeSerializer(like)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            like = self.get_object(pk, profile)
            post = like.group_post
            with transaction.atomic():
                like.delete()
                post.likes_count = F('likes_count') - 1
                post.save(update_fields=['likes_count'])
            return Response({"message": "Like deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupPostCommentLikeToggleAPIView(APIView):
    """
    POST: Toggle like/unlike for a group post comment (by comment id)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            comment_id = request.data.get("comment_id")
            if not comment_id:
                return Response(error_response("comment_id required."), status=status.HTTP_400_BAD_REQUEST)
            comment = get_object_or_404(GroupPostComment, id=comment_id)
            existing_like = GroupPostCommentLike.objects.filter(comment=comment, profile=profile).first()
            with transaction.atomic():
                if existing_like:
                    existing_like.delete()
                    # Avoid like_count underflow
                    GroupPostComment.objects.filter(id=comment.id, like_count__gt=0).update(
                        like_count=F("like_count") - 1
                    )
                    comment.refresh_from_db(fields=["like_count"])
                    return Response({"message": "Like removed.", "like_count": comment.like_count}, status=200)
                else:
                    GroupPostCommentLike.objects.create(comment=comment, profile=profile)
                    GroupPostComment.objects.filter(id=comment.id).update(
                        like_count=F("like_count") + 1
                    )
                    comment.refresh_from_db(fields=["like_count"])
                    serializer = GroupPostCommentLikeSerializer(
                        GroupPostCommentLike.objects.get(comment=comment, profile=profile)
                    )
                    try:
                        transaction.on_commit(lambda: notify_owner_of_group_comment_like.delay(comment.id, profile.id))
                    except:
                        pass
                    return Response(success_response(serializer.data), status=201)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupPostCommentLikeListAPIView(APIView, PaginationMixin):
    """
    GET /groups/post-comments/<comment_id>/likes/
    Returns paginated list of likes on a group post comment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, comment_id):
        try:
            comment = get_object_or_404(GroupPostComment, id=comment_id)
            likes_qs = GroupPostCommentLike.objects.filter(comment=comment).order_by('-created_at')
            paginated_likes = self.paginate_queryset(likes_qs, request)
            serializer = GroupPostCommentLikeSerializer(paginated_likes, many=True)
            return self.get_paginated_response(serializer.data)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupJoinRequestCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        try:
            group = get_object_or_404(Group, id=group_id)
            profile = get_user_profile(request.user)

            # Already a member check
            if GroupMember.objects.filter(group=group, profile=profile).exists():
                return Response(error_response("You are already a member of this group."), status=status.HTTP_400_BAD_REQUEST)

            if group.privacy == 'public':
                with transaction.atomic():
                    # Auto add as viewer without any request
                    group_member = GroupMember.objects.create(
                        group=group,
                        profile=profile,
                        role=RoleChoices.VIEWER,
                        assigned_by=None  # or system user
                    )
                    group.member_count = GroupMember.objects.filter(group=group).count()
                    group.save(update_fields=['member_count'])
                    
                    # Add to ChatGroupMember
                    ChatGroupMember.objects.create(
                        group=group.chat_group,
                        profile=profile
                    )
                    try:
                        transaction.on_commit(lambda:send_group_join_notifications_task.delay(group.id, profile.id, action='joined',sender_id=profile.id))
                    except:
                        pass
                    
                    log_group_action(group, profile, GroupAction.PUBLIC_JOIN, "Group member has joined group as it is public", group_member=group_member)
                return Response(success_response({"message": "You have successfully joined the group as a viewer."}), status=status.HTTP_201_CREATED)

            # PRIVATE: Check if request already exists
            join_request, created = GroupJoinRequest.objects.get_or_create(group=group, profile=profile)

            if not created and join_request.status == 'pending':
                return Response(error_response("You have already requested to join this group."), status=status.HTTP_400_BAD_REQUEST)

            join_request.status = 'pending'
            join_request.message = request.data.get('message', '')
            join_request.save()
            log_group_action(group, profile, GroupAction.JOIN_REQUEST, "Group member has requested to join", member_request=join_request)
            return Response(success_response({"message": "Join request sent successfully."}), status=status.HTTP_201_CREATED)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupJoinRequestListAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get(self, request, group_id):
        try:
            group = get_object_or_404(Group, id=group_id)
            self.check_object_permissions(request, group)

            requests_qs = GroupJoinRequest.objects.filter(group=group, status='pending').select_related('profile')
            paginated_qs = self.paginate_queryset(requests_qs, request)
            serializer = GroupJoinRequestSerializer(paginated_qs, many=True)
            return self.get_paginated_response(serializer.data)

        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupJoinRequestActionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdminOrModerator]

    def put(self, request, group_id, request_id):
        try:
            group = get_object_or_404(Group, id=group_id)
            self.check_object_permissions(request, group)
            
            join_request = get_object_or_404(GroupJoinRequest, id=request_id, group=group)
            
            if not join_request.status == JoiningRequestStatus.PENDING:
                return Response(success_response('Already responded'), status=status.HTTP_200_OK)

            action = request.data.get('action')
            role = request.data.get('role')
            if action not in ['accept', 'reject']:
                return Response(error_response("Invalid action. Use 'accept' or 'reject'."), status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                if action == 'accept':
                    join_request.status = JoiningRequestStatus.ACCEPTED
                    join_request.save()

                    # Add user as a group member
                    group_member = GroupMember.objects.create(
                        group=group,
                        profile=join_request.profile,
                        role=role if role else RoleChoices.VIEWER,
                        assigned_by=get_user_profile(request.user)
                    )

                    # Also add them to chat group
                    ChatGroupMember.objects.create(
                        group=group.chat_group,
                        profile=join_request.profile
                    )
                    
                    group.member_count = GroupMember.objects.filter(group=group).count()
                    group.save(update_fields=['member_count'])

                    # async notification
                    transaction.on_commit(
                        lambda: send_group_join_notifications_task.delay(
                            group.id, join_request.profile.id, action='accepted',
                            sender_id=get_user_profile(request.user).id
                        )
                    )

                elif action == 'reject':
                    join_request.status = JoiningRequestStatus.REJECTED
                    join_request.save()

                    transaction.on_commit(
                        lambda: send_group_join_notifications_task.delay(
                            group.id, join_request.profile.id, action='rejected',
                            sender_id=get_user_profile(request.user).id
                        )
                    )
            return Response(success_response({"message": f"Request {action}ed successfully."}), status=status.HTTP_200_OK)
        
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateGroupPostCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, comment_id):
        """
        Update the content of a group post comment.
        """
        try:
            comment = get_object_or_404(GroupPostComment, id=comment_id)

            # Optional: Check if the authenticated user is the comment owner
            profile = get_user_profile(request.user)
            if comment.profile != profile:
                return Response(
                    error_response("You do not have permission to update this comment."),
                    status=status.HTTP_403_FORBIDDEN
                )

            data = request.data.copy()
            serializer = GroupPostCommentSerializer(comment, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        

class DeleteGroupPostCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """
        comment owner and post owner can delete this comment
    """

    def delete(self, request, comment_id):
        """
        Soft delete (or hard delete) a group post comment.
        """
        try:
            comment = get_object_or_404(GroupPostComment, id=comment_id)

            profile = get_user_profile(request.user)
            post_owner = comment.group_post.profile
            if comment.profile != profile and post_owner != profile:
                return Response(
                    error_response("You do not have permission to delete this comment."),
                    status=status.HTTP_403_FORBIDDEN
                )

            if hasattr(comment, 'is_active'):
                comment.is_active = False
                comment.save(update_fields=['is_active'])
            else:
                comment.delete()

            if comment.parent is None:
                group_post = comment.group_post
                total_top_level_comments = GroupPostComment.objects.filter(
                    group_post=group_post,
                    is_active=True if hasattr(comment, 'is_active') else True,
                    parent__isnull=True
                ).count()
                GroupPost.objects.filter(id=group_post.id).update(comments_count=total_top_level_comments)

            return Response(
                {"status": True, "message": "Comment deleted successfully."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)


class TrendingGroupsAPIView(APIView, PaginationMixin):
    def get(self, request):
        try:
            groups = Group.objects.filter(is_active=True).order_by('-trending_score')
            paginated_qs= self.paginate_queryset(groups,request)
            serializer = GroupListSerializer(paginated_qs, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupyHashTagAPIView(APIView, PaginationMixin):
    """
    Get all groups for a given hashtag name.
    """

    def get(self, request, hashtag_name):
        
        # Get the hashtag by name (case-insensitive) or return 404
        hashtag = get_object_or_404(HashTag, name__iexact=hashtag_name)

        # Filter groups linked to this hashtag
        groups = Group.objects.filter(tags=hashtag).order_by("-trending_score")

        paginated_qs = self.paginate_queryset(groups, request)
        serializer = GroupListSerializer(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)


class RecommendedGroupsAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)

        # Step 1: Groups user is already a member of
        user_groups = Group.objects.filter(members__profile=profile)

        # Step 2: Collect hashtags from these groups
        hashtags = HashTag.objects.filter(groups__in=user_groups).distinct()

        # Step 3: Find other groups with these hashtags, exclude groups user is already in
        recommended_groups = (
            Group.objects.filter(tags__in=hashtags)
            .exclude(id__in=user_groups.values_list("id", flat=True))
            .distinct()
            .order_by("-trending_score")
        )

        # Step 4: Paginate & serialize
        paginated_qs = self.paginate_queryset(recommended_groups, request)
        serializer = GroupListSerializer(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)


class FlagGroupPostAPIView(APIView):
    def post(self, request, post_id):
        try:
            post = GroupPost.objects.get(id=post_id)
            profile = get_user_profile(request.user)

            serializer = GroupPostFlagSerializer(
                data=request.data,
                # context={"profile": profile, "post": post}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(reported_by=profile, post=post)

            # Increment flag count
            post.flag_count = F('flag_count') + 1
            post.is_flagged = True
            post.save(update_fields=["flag_count", "is_flagged"])

            return Response(success_response("Post flagged successfully"), status=status.HTTP_201_CREATED)

        except GroupPost.DoesNotExist:
            return Response(error_response("Post not found"), status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return Response(error_response("You have already flagged this post"), status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupFlaggedPostsAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated, IsGroupAdmin]
    def get(self, request, group_id):
        try:
            
            flagged_posts =GroupPostFlag.objects.filter(
                post__group_id=group_id
                ).select_related(
                    "post", "reported_by", "post__group", "post__profile"
                    ).order_by("-created_at")
                
            paginated_qs = self.paginate_queryset(flagged_posts, request)
            serializer = GroupPostFlagListSerializer(paginated_qs, many=True)
            return self.get_paginated_response(serializer.data)
        
        except PermissionDenied as e:
            return Response(error_response("You do not have permission to perform this action."), status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupMemberLeaderboardListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id=None, slug=None):
        try:
            
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(slug=slug)

            # Fetch all active members
            members = GroupMember.objects.select_related('profile').filter(group=group).order_by("-activity_score", "profile__username")

            serializer = GroupMemberSerializer(members, many=True, context={'request':request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response(error_response("Group not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupEventsListAPIView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"status": False, "message": "Group not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        events = group.events.all().order_by('-start_datetime')
        paginated_qs = self.paginate_queryset(events, request)
        serializer = EventListSerializer(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)

class GroupActionLogListAPIView(APIView, PaginationMixin):
    """
    GET /api/groups/logs/
    Returns a paginated list of group action logs.
    
    Query Parameters:
        - group_id (int): Filter logs by group.
        - action (str): Filter by action type (choices from GroupAction).
        - profile_id (int): Filter by profile.
        - start_date (YYYY-MM-DD): Filter logs created on or after this date.
        - end_date (YYYY-MM-DD): Filter logs created on or before this date.
    
    Permissions:
        - Requires authentication.
    
    Response:
        Paginated JSON list of logs with group & profile details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logs = GroupActionLog.objects.select_related("group", "profile").all()

            # Apply filters
            group_id = request.query_params.get("group_id")
            if group_id:
                logs = logs.filter(group_id=group_id)

            action = request.query_params.get("action")
            if action:
                logs = logs.filter(action__iexact=action)

            profile_id = request.query_params.get("profile_id")
            if profile_id:
                logs = logs.filter(profile_id=profile_id)

            username = request.query_params.get("username")
            if username:
                logs = logs.filter(profile__username__iexact=username)

            start_date = request.query_params.get("start_date")
            if start_date:
                parsed_start = parse_date(start_date)
                if parsed_start:
                    logs = logs.filter(created_at__date__gte=parsed_start)

            end_date = request.query_params.get("end_date")
            if end_date:
                parsed_end = parse_date(end_date)
                if parsed_end:
                    logs = logs.filter(created_at__date__lte=parsed_end)

            # Pagination
            paginated_logs = self.paginate_queryset(logs, request)
            serializer = GroupActionLogSerializer(paginated_logs, many=True, context={"request": request})

            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=500)


class MyGroupsListAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_profile(request.user)
        is_owner = request.query_params.get("is_owner")
        role = request.query_params.get("role")

        try:
            # Base queryset: groups where the user is a member
            memberships = GroupMember.objects.select_related("group").filter(profile=profile)

            # Filter: is_owner (groups created by me)
            if is_owner and is_owner.lower() == "true":
                memberships = memberships.filter(group__creator=profile)

            # Filter: role
            if role:
                memberships = memberships.filter(role=role)

            # Extract groups from memberships
            groups_qs = Group.objects.filter(id__in=memberships.values_list("group_id", flat=True))
            
            # Paginate groups
            paginated_groups = self.paginate_queryset(groups_qs, request)
            serialized_groups = GroupListSerializer(paginated_groups, many=True, context={"request": request}).data

            return self.get_paginated_response(serialized_groups)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class GroupSearchAPIView(APIView, PaginationMixin):
    """
    Search groups by name or description with pagination.
    Anyone can see all groups (public or private).
    """
    permission_classes = [AllowAny]
    def get(self, request):
        query = request.GET.get('name', '').strip()
        if not query:
            return Response({"detail": "Query parameter 'name' is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        groups = Group.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).order_by('-trending_score', '-last_activity_at')
        
        paginated_qs = self.paginate_queryset(groups, request)
        serializer = GroupSearchSerializer(paginated_qs, many=True, context={'request': request})
        return self.get_paginated_response(success_response(serializer.data))
    

class GroupsFeedAPIView(APIView, PaginationMixin):
    """
    Single endpoint to fetch groups feed for authenticated users.
    Params:
    - type: 'new', 'trending', 'recommended'
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        feed_type = request.GET.get("type", "new").lower()  # default: new
        try:
            try:
                profile = get_user_profile(request.user)
            except Profile.DoesNotExist:
                return Response(
                    error_response("User profile not found"),
                    status=status.HTTP_404_NOT_FOUND
                )

            # NEW GROUPS
            if feed_type == "new":
                groups = Group.objects.select_related('creator').order_by('-created_at')

            # TRENDING GROUPS
            elif feed_type == "trending":
                groups = Group.objects.filter(is_active=True).order_by('-trending_score', '-last_activity_at')

            # RECOMMENDED GROUPS
            elif feed_type == "recommended":
                user_groups = Group.objects.filter(members__profile=profile)
                hashtags = HashTag.objects.filter(groups__in=user_groups).distinct()
                groups = (
                    Group.objects.filter(tags__in=hashtags)
                    .exclude(id__in=user_groups.values_list("id", flat=True))
                    .distinct()
                    .order_by('-trending_score', '-last_activity_at')
                )

            # INVALID TYPE
            else:
                return Response(
                    error_response("Invalid type parameter"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # PAGINATION
            paginated_qs = self.paginate_queryset(groups, request)

            # SERIALIZE
            serializer = GroupListSerializer(paginated_qs, many=True, context={'request': request})

            return self.get_paginated_response(success_response(serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GroupSuggestionAPIView(APIView):
    """
    Suggest groups to a user based on mutual interests (tags),
    excluding groups the user is already a member of.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            # 1. Get the target profile
            try:
                profile = Profile.objects.get(id=profile_id)
            except Profile.DoesNotExist:
                return Response(
                    error_response("Profile not found"),
                    status=status.HTTP_404_NOT_FOUND
                )

            # 2. Get groups the user is already a member of
            joined_group_ids = GroupMember.objects.filter(profile=profile).values_list('group_id', flat=True)


            # 3. Collect tags from groups the user is associated with
            profile_tags = HashTag.objects.filter(groups__creator=profile).distinct()

            if not profile_tags.exists():
                # No tags, return empty list
                return Response(success_response([]), status=status.HTTP_200_OK)

            # 4. Find other groups with these tags, excluding already joined groups
            suggested_groups = (
                Group.objects.filter(tags__in=profile_tags)
                .exclude(id__in=joined_group_ids)
                .annotate(common_tags_count=Count('tags'))
                .distinct()
                .order_by('-common_tags_count', '-trending_score', '-last_activity_at')  # prioritize mutual interests
            )

            # 5. Serialize & return
            serializer = GroupSuggestionSerializer(suggested_groups, many=True, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicGroupMemberListAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, group_id=None, slug=None):
        try:
            
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(slug=slug)
                
            if not group.show_members:
                return Response(error_response('Group members are private'), status=status.HTTP_403_FORBIDDEN)

            # Fetch all active members
            members = GroupMember.objects.select_related('profile').filter(group=group)

            serializer = GroupMemberSerializer(members, many=True, context={'request':request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response(error_response("Group not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreatedGroupsAPIView(APIView, PaginationMixin):
    """
    GET /api/groups/my-created/
    Returns list of groups created by the logged-in profile
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            groups = Group.objects.filter(creator=profile).prefetch_related("tags")
            
            paginated_qs = self.paginate_queryset(groups, request)
            serializer = BasicGroupDetailSerializer(paginated_qs, many=True)
            return self.get_paginated_response(serializer.data)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=400)


class LeaveGroupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        try:
            profile = request.user.profile
            group = Group.objects.get(id=group_id)

            # Check if member exists
            try:
                membership = GroupMember.objects.get(profile=profile, group=group)
            except GroupMember.DoesNotExist:
                return Response(
                    error_response("You are not a member of this group."),
                    status=400
                )

            # Prevent group creator from leaving
            if group.creator == profile:
                return Response(
                    error_response("Group creator cannot leave the group."),
                    status=400
                )

            # Delete membership
            membership.delete()

            # Decrement member count safely
            if group.member_count > 0:
                group.member_count -= 1
                group.save(update_fields=["member_count"])

            return Response(
                success_response({"message": f"You have left the group '{group.name}'."}),
                status=200
            )

        except Group.DoesNotExist:
            return Response(error_response("Group not found."), status=404)
        except Exception as e:
            return Response(error_response(str(e)), status=400)
