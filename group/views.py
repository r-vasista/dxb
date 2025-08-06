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
# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
)
from group.choices import (
    RoleChoices
)
from group.serializers import (
    GroupCreateSerializer, GroupPostSerializer, GroupDetailSerializer, GroupPostCommentSerializer, AddGroupMemberSerializer, GroupMemberSerializer, 
    GroupListSerializer, GroupUpdateSerializer, GroupMemberUpdateSerializer
)
from group.permissions import (
    can_add_members, IsGroupAdminOrModerator, IsGroupAdmin
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
                serializer.save()
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
        

class AddGroupPostCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            profile = get_actual_user(request.user)
            group_post = GroupPost.objects.get(id=post_id)
            data = request.data.copy()
            data['group_post'] = post_id
            data['profile'] = profile.id
            serializer = GroupPostCommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            if not serializer.validated_data.get('parent'):
                group_post.comments_count = F('comments_count') + 1
                group_post.save(update_fields=['comments_count'])

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)


class ListGroupPostCommentsAPIView(APIView,PaginationMixin):
    permission_classes = [IsAuthenticated]
    def get(self, request, post_id):
        try:
            # Only top-level comments (parent=None)
            comments = GroupPostComment.objects.filter(group_post_id=post_id, parent=None, is_active=True)
            paginated_queryset = self.paginate_queryset(comments,request)
            serializer = GroupPostCommentSerializer(paginated_queryset, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
            member = request.data.get('profile')

            member = get_object_or_404(GroupMember, profile=member, group=group)

            serializer = GroupMemberUpdateSerializer(member, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            serializer.save()

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

            member = get_object_or_404(GroupMember, profile=member, group=group)

            member.delete()

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
