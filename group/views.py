# Rest Framework imports
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser

# Djnago imports
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import F

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
)
from group.choices import (
    RoleChoices
)
from group.serializers import (
    GroupCreateSerializer, GroupPostSerializer, GroupDetailSerializer, GroupPostCommentSerializer, AddGroupMemberSerializer, GroupMemberSerializer, 
    GroupListSerializer, GroupPostLikeSerializer, GroupPostCommentLikeSerializer
)
from group.permissions import (
    can_add_members
)
from core.services import (
    success_response, error_response, get_user_profile, get_actual_user
)
from group.utils import (
    can_post_to_group, handle_grouppost_hashtags
)
from core.pagination import PaginationMixin

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

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
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

    def post(self,request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            profile=get_actual_user(request.user)

            if not can_post_to_group(group,profile):
                return Response(error_response("You do not have permission to post in this group."),
                                 status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['group'] = group.id
            data['profile'] = profile.id
            serializer = GroupPostSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            post=serializer.save()
            handle_grouppost_hashtags(post)
            return Response(success_response,(serializer.data),status=status.HTTP_201_CREATED)
        except Group.DoesNotExist:
            return Response(error_response("Group Does not found"))
        except ValidationError as e :
            return Response(error_response(e.detail))
        except Exception as e :
            return Response(error_response(str(e)),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
       
        
class GroupListAPIView(APIView):

    permission_classes =[IsAuthenticated]

    def get(self,request,groupid):
        try:
            group= Group.objects.get(id=groupid)
            query_parms = {}
            is_pinned = request.query_parms.get('is_pinned')
            if is_pinned is not None:
                query_parms ['is_pinned'] = is_pinned.lower() == 'true'
                posts =GroupPost.objects.select_related('profile').filter(
                    group=group,**query_parms).order_by('is_pinned','-created_at')
                serializer=GroupPostSerializer(posts,many=True)
                return Response(success_response(serializer.data),status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response(error_response("Group Does not Found"),status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

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
            post.delete()
            return Response(success_response("Post Was Delted SucessFully"),status=status.HTTP_204_NO_CONTENT)
        except GroupPost.DoesNotExist:
            return Response(error_response("Group Post Does not found"))
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

            serializer = GroupPostSerializer(post)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except GroupPost.DoesNotExist:
            return Response(error_response("Group post not found."), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)       
        

class CreateGroupPostCommentAPIView(APIView):
    """
    API view to create comments/replies for a group post.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            profile = get_actual_user(request.user)
            group_post = get_object_or_404(GroupPost, id=post_id)
            
            data = request.data.copy()
            data['group_post'] = group_post.id
            data['profile'] = profile.id

            # Optional: validate parent
            parent_id = data.get("parent")
            if parent_id:
                parent_comment = GroupPostComment.objects.filter(id=parent_id, group_post=group_post).first()
                if not parent_comment:
                    return Response(error_response("Invalid parent comment."),
                                    status=status.HTTP_400_BAD_REQUEST)

            serializer = GroupPostCommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            comment = serializer.save()

            # If top-level, increment comments_count on post
            if not serializer.validated_data.get('parent'):
                group_post.comments_count = F('comments_count') + 1
                group_post.save(update_fields=['comments_count'])

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)


class ParentGroupPostCommentsAPIView(APIView, PaginationMixin):
    """
    List all top-level comments for a group post (paginated).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            comments = GroupPostComment.objects.select_related('profile', 'parent').filter(
                group_post__id=post_id, parent__isnull=True, is_active=True
            ).order_by('-created_at')
            
            paginated_comments = self.paginate_queryset(comments, request)
            serializer = GroupPostCommentSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChildGroupPostCommentListAPIView(APIView, PaginationMixin):
    """
    List all child comments/replies for a parent comment on a group post (paginated).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id, parent_id):
        try:
            group_post = get_object_or_404(GroupPost, id=post_id)
            comments = GroupPostComment.objects.select_related('profile', 'parent').filter(
                group_post=group_post, parent_id=parent_id, is_active=True
            ).order_by('created_at')

            paginated_comments = self.paginate_queryset(comments, request)
            serializer = GroupPostCommentSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class GroupAddMemberAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            # 1. Fetch group
            group = get_object_or_404(Group, id=data.get('group'))
            
            # 2. Get request user's profile
            acting_profile = get_user_profile(request.user)

            # 3. Check permission: Only Admin or Moderator can add members
            if not can_add_members(group, acting_profile):
                return Response(error_response("You do not have permission to add members."),
                                status=status.HTTP_403_FORBIDDEN)
                
            # 4. Save new member
            serializer = AddGroupMemberSerializer(data=data, context={'group': group})
            serializer.is_valid(raise_exception=True)
            serializer.save(assigned_by=acting_profile)

            # Update group member count
            group.member_count = GroupMember.objects.filter(group=group).count()
            group.save(update_fields=['member_count'])

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
                    comment.like_count = F("like_count") - 1
                    comment.save(update_fields=["like_count"])
                    return Response({"message": "Like removed."}, status=status.HTTP_200_OK)
                else:
                    like = GroupPostCommentLike.objects.create(comment=comment, profile=profile)
                    comment.like_count = F("like_count") + 1
                    comment.save(update_fields=["like_count"])
                    serializer = GroupPostCommentLikeSerializer(like)
                    return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
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
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
