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
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Count, Q, F

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupJoinRequest
)
from group.choices import (
    RoleChoices, JoiningRequestStatus, GroupAction
)
from group.serializers import (
    GroupCreateSerializer, GroupPostSerializer, GroupDetailSerializer, GroupPostCommentSerializer, AddGroupMemberSerializer, GroupMemberSerializer, 
    GroupListSerializer, GroupPostLikeSerializer, GroupPostCommentLikeSerializer, GroupUpdateSerializer, GroupMemberUpdateSerializer, 
    GroupJoinRequestSerializer
)
from group.permissions import (
    can_add_members, IsGroupAdminOrModerator, IsGroupAdmin
)
from group.utils import (
    can_post_to_group, handle_grouppost_hashtags, log_group_action
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
                extract_and_assign_hashtags(group.description, group)
                
                log_group_action(group, profile, GroupAction.CREATE, "Group created by user")

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        
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


class GroupDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, group_id=None, group_name=None):
        try:
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(name__iexact=group_name)
                
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
            filters = {'group': group}
            is_pinned = request.query_params.get('is_pinned')

            if is_pinned is not None:
                filters['is_pinned'] = is_pinned.lower() == 'true'

            posts = GroupPost.objects.select_related('profile').filter(
                **filters
            ).order_by('-is_pinned', '-created_at')

            paginated_posts = self.paginate_queryset(posts, request)
            serializer = GroupPostSerializer(
                paginated_posts, many=True, context={'request': request}
            )

            return self.get_paginated_response(serializer.data)

        except Group.DoesNotExist:
            return Response(
                error_response("Group Not Found"), status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
      

class GroupPostDetailAPIView(APIView):

    permission_classes =  [IsAuthenticated]
    def get(self,request,post_id):

        try:
            post = GroupPost.objects.get(id=post_id)
            serializer =  GroupPostSerializer(post)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except GroupPost.DoesNotExist:
            return Response(error_response("Group post not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self,request,post_id):
        try:
            post = GroupPost.objects.get(id=post_id)
            profile = get_user_profile(request.user)

            is_author = post.profile == profile
            group_member = GroupMember .objects.filter(group=post.group,
                                profile=profile,is_banned=False).first()
            allowed_roles = [RoleChoices.ADMIN,RoleChoices.MODERATOR]
            is_privileged = group_member and group_member.role in allowed_roles

            if not (is_author or is_privileged):
                return Response(error_response("you do not have permission to delete this post"),status=status.HTTP_403_FORBIDDEN)
            log_group_action(post.group, profile, GroupAction.POST_DELETE, "Group post deleted by user")
            post.delete()
            return Response(success_response("Post Was Delted SucessFully"),status=status.HTTP_200_OK)
        except GroupPost.DoesNotExist:
            return Response(error_response("Group Post Does not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)),status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
    def put(self, request, post_id):
        try:
            post = GroupPost.objects.get(id=post_id)
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

            if updated:
                post.save()
            log_group_action(post.group, profile, GroupAction.POST_UPDATE, "Group post updated by user", group_post=post)

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
                
            # 4. Save new member
            serializer = AddGroupMemberSerializer(data=data, context={'group': group})
            serializer.is_valid(raise_exception=True)
            member = serializer.save(assigned_by=acting_profile)

            # Update group member count
            group.member_count = GroupMember.objects.filter(group=group).count()
            group.save(update_fields=['member_count'])
            log_group_action(group, acting_profile, GroupAction.MEMBER_ADD, "Group member added", group_member=member)

            return Response(success_response({"message": "Member added successfully."}),
                            status=status.HTTP_201_CREATED)
        except ValueError as e:
                return Response(error_response(str(e)), status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
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

            serializer.save()
            log_group_action(group, member.profile, GroupAction.MEMBER_UPDATE, "Group member role updated", group_member=member)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
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

            group_member.delete()
            log_group_action(group, member, GroupAction.MEMBER_REMOVE, "Group member role updated")

            return Response(success_response("Member removed successfully"), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GroupMemberListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id=None, group_name=None):
        try:
            
            if group_id:
                group = Group.objects.get(pk=group_id)
            else:
                group = Group.objects.get(name__iexact=group_name)

            # Fetch all active members
            members = GroupMember.objects.select_related('profile').filter(group=group)

            serializer = GroupMemberSerializer(members, many=True, context={'request':request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response(error_response("Group not found"), status=status.HTTP_404_NOT_FOUND)
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
                # Auto add as viewer without any request
                GroupMember.objects.create(
                    group=group,
                    profile=profile,
                    role=RoleChoices.VIEWER,
                    assigned_by=None  # or system user
                )
                return Response(success_response({"message": "You have successfully joined the group as a viewer."}), status=status.HTTP_201_CREATED)

            # PRIVATE: Check if request already exists
            join_request, created = GroupJoinRequest.objects.get_or_create(group=group, profile=profile)

            if not created and join_request.status == 'pending':
                return Response(error_response("You have already requested to join this group."), status=status.HTTP_400_BAD_REQUEST)

            join_request.status = 'pending'
            join_request.message = request.data.get('message', '')
            join_request.save()

            return Response(success_response({"message": "Join request sent successfully."}), status=status.HTTP_201_CREATED)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupJoinRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsGroupAdmin]

    def get(self, request, group_id):
        try:
            group = get_object_or_404(Group, id=group_id)
            self.check_object_permissions(request, group)

            requests_qs = GroupJoinRequest.objects.filter(group=group, status='pending').select_related('profile')
            serializer = GroupJoinRequestSerializer(requests_qs, many=True)

            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
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

            if action == 'accept':
                join_request.status = 'accepted'
                join_request.save()

                # Add user as a member
                GroupMember.objects.create(
                    group=group,
                    profile=join_request.profile,
                    role=role if role else RoleChoices.VIEWER,
                    assigned_by=get_user_profile(request.user)
                )

            elif action == 'reject':
                join_request.status = 'rejected'
                join_request.save()

            return Response(success_response({"message": f"Request {action}ed successfully."}), status=status.HTTP_200_OK)
        
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

    def delete(self, request, comment_id):
        """
        Soft delete (or hard delete) a group post comment.
        """
        try:
            comment = get_object_or_404(GroupPostComment, id=comment_id)

            profile = get_user_profile(request.user)
            if comment.profile != profile:
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
