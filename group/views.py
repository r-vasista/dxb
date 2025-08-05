# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.serializers import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser

# Djnago imports
from django.db import transaction

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
)
from group.choices import (
    RoleChoices
)
from group.serializers import (
    GroupCreateSerializer, GroupPostSerializer
)
from core.services import (
    success_response, error_response, get_user_profile, get_actual_user
)
from group.utils import (
    can_post_to_group
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

            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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