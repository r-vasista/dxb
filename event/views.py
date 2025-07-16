# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser

# Django imports
from django.utils import timezone
from django.db.models import Q

# Local imports
from event.serializers import (
    EventCreateSerializer, EventListSerializer, EventAttendanceSerializer, EventSummarySerializer, EventMediaSerializer
)
from event.models import (
    Event, EventAttendance, EventMedia
)
from event.choices import (
    EventStatus
)
from core.services import success_response, error_response, get_user_profile
from core.pagination import PaginationMixin
from core.permissions import is_owner_or_org_member

class CreateEventAPIView(APIView):
    """
    POST /api/events/create/ 
    Creates a new event for the logged-in profile.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            data=request.data
            data['host'] = profile.id

            serializer = EventCreateSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            event = serializer.save()
            
            return Response(success_response(data=serializer.data), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventListAPIView(APIView, PaginationMixin):
    """
    GET /api/events/hierarchical/
    Returns events based on:
    1. Same city → 2. Same state → 3. Same country
    Also includes online events.
    If no location: return upcoming events by date.
    Supports pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)
            online_events = Event.objects.filter(is_online=True, status='published')

            if profile.city and profile.state and profile.country:
                city_events = Event.objects.filter(city=profile.city, is_online=False, status='published')
                if city_events.exists():
                    events = city_events | online_events
                else:
                    state_events = Event.objects.filter(state=profile.state, is_online=False, status='published')
                    if state_events.exists():
                        events = state_events | online_events
                    else:
                        country_events = Event.objects.filter(country=profile.country, is_online=False, status='published')
                        events = country_events | online_events
            else:
                events = Event.objects.filter(status='published').order_by('start_datetime')

            # Apply pagination
            queryset = events.distinct().order_by('start_datetime')
            paginated_qs = self.paginate_queryset(queryset, request)
            serializer = EventListSerializer(paginated_qs, many=True, context={'request': request})

            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventAttendacneAPIView(APIView):
    """
    API for Event RSVP
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            data['profile'] = get_user_profile(request.user).id
            serializer = EventAttendanceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, event_id):
        try:
            event_attendance = EventAttendance.objects.select_related('profile').filter(id=event_id)
            serializer = EventAttendanceSerializer(event_attendance, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self, request):
        try:
            profile = get_user_profile(request.user)
            event_id = request.data.get('event')
            status_value = request.data.get('status')

            if not event_id or not status_value:
                return Response(error_response( "Both 'event' and 'status' fields are required."), status=status.HTTP_400_BAD_REQUEST)

            try:
                attendance = EventAttendance.objects.get(profile=profile, event_id=event_id)
            except EventAttendance.DoesNotExist:
                return Response(error_response("RSVP does not exist. You must RSVP first before updating."), status=status.HTTP_404_NOT_FOUND)
            data = {'status': status_value}
            serializer = EventAttendanceSerializer(attendance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(success_response( {
                    "event": attendance.event.title,
                    "status": attendance.status
                }),  status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class MyRSVPEventsListAPIView(APIView):
    """
    API that lists all the events to be attended by the user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user_profile = get_user_profile(request.user)
            current_datetime = timezone.now()
            
            # Get all upcoming events where user is attending
            upcoming_events = Event.objects.prefetch_related(
                'attendees'
            ).filter(
                Q(attendees=user_profile) &
                Q(start_datetime__gte=current_datetime) &
                Q(status=EventStatus.PUBLISHED)
            ).order_by('start_datetime')
            
            # Optional: Filter by attendance status if needed
            attendance_status = request.query_params.get('attendance_status')
            if attendance_status:
                upcoming_events = upcoming_events.filter(
                    eventattendance__profile=user_profile,
                    eventattendance__status=attendance_status
                )
                            
            serializer = EventSummarySerializer(upcoming_events, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaUploadAPIView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            profile = get_user_profile(request.user)

            # Permission check
            if not is_owner_or_org_member(event.host, request.user):
                return Response(error_response("You do not have permission to upload media to this event."), status=status.HTTP_403_FORBIDDEN)
            
            # File validation
            file = request.FILES.get('file')
            if not file:
                return Response(error_response("No file uploaded."), status=status.HTTP_400_BAD_REQUEST)

           # Prepare data for serializer
            data = request.data
            data['event'] = event.id
            data['uploaded_by'] = profile.id
            
            # Create serializer and validate
            serializer = EventMediaSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            
            # Save the media
            serializer.save()
            
            return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except Event.DoesNotExist:
            return Response(error_response("Event not found."), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaListAPIView(APIView):
    """
    GET /api/events/<event_id>/media/
    Returns all media items (images, videos, docs) for a given event.
    """

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            media_qs = EventMedia.objects.filter(event=event, is_active=True).order_by('-uploaded_at')
            serializer = EventMediaSerializer(media_qs, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Event.DoesNotExist:
            return Response(error_response("Event not found."), status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateEventAPIView(APIView):
    """
    PUT /api/events/<int:event_id>/update/
    Updates an existing event.
    Only host or authorized org member can update the event.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, event_id):
        try:
            profile = get_user_profile(request.user)
            event = Event.objects.get(id=event_id)

            if not is_owner_or_org_member(event.host, request.user):
                return Response(error_response("You do not have permission to update this event."), status=status.HTTP_403_FORBIDDEN)

            data = request.data.copy()
            data['host'] = event.host.id  # preserve original host

            serializer = EventCreateSerializer(event, data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

        except Event.DoesNotExist:
            return Response(error_response("Event not found."), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
