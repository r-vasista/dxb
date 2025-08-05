from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
# Create your views here.

from group. models import Group,GroupMember,GroupPost
from group.serializers import GroupPostSerializer

from group.utils import can_post_to_group

from core.services import error_response, get_actual_user,success_response

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