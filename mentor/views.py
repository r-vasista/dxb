from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


#from local
from .models import MentorProfile
from profiles.models import Profile
from core.services import get_user_profile

from mentor.serializers import MentorProfileSerializer
from mentor.choices import MentorStatus
# Create your views here.'

class MentorProfileCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        try:
            profile=get_user_profile(request.user)

            if not profile.mentor_eligibile or profile.mentor_blacklisted:
                return Response({
                    "status": False,
                    "message": "You are not eligible to become a mentor or you are blacklisted."
                }, status=status.HTTP_403_FORBIDDEN)
            if hasattr(profile,'mentor_profile'):
                return Response({
                    "status": False,
                    "message": "Mentor profile already exists."
                }, status=status.HTTP_400_BAD_REQUEST)
            serializer = MentorProfileSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(profile=profile)
                return Response({
                    "status": True,
                    "message": "Mentor profile created successfully.",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "status": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Something went wrong: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class MentorProfileDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            mentor_profile = profile.mentor_profile
            if mentor_profile.status == MentorStatus.SUSPENDED:
                return Response({
                    "status": False, 
                    "message": "Mentor Profile is Suspended"
                }, status=status.HTTP_403_FORBIDDEN)
            serializer = MentorProfileSerializer(mentor_profile)
            return Response({"status": True,"data": serializer.data})
        except MentorProfile.DoesNotExist:
            return Response({"status": False,"message": "Mentor profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:return Response({"status": False,"message": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            mentor_profile = profile.mentor_profile

            # Optional: Only allow owners 
            if get_user_profile(request.user) != profile :
                return Response({"status": False, "message": "You are not allowed to update this mentor profile."},
                                 status=status.HTTP_403_FORBIDDEN)

            serializer = MentorProfileSerializer(mentor_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": True,
                    "message": "Mentor profile updated successfully.",
                    "data": serializer.data
                })
            return Response({
                "status": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MentorProfile.DoesNotExist:
            return Response({
                "status": False,
                "message": "Mentor profile not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
