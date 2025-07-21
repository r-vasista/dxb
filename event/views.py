# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from django.db import transaction
# Django imports
from django.utils import timezone
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from django.http import Http404

# Local imports
from event.serializers import (
    EventCreateSerializer, EventListSerializer, EventAttendanceSerializer, EventSummarySerializer, EventMediaSerializer, 
    EventCommentSerializer, EventCommentListSerializer, EventMediaCommentSerializer, EventDetailSerializer
)
from event.models import (
    Event, EventAttendance, EventMedia, EventComment, EventMediaComment
)
from notification.task import (
    send_event_creation_notification_task, send_event_rsvp_notification_task, send_event_media_notification_task, 
    shared_event_comment_notification_task
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
            transaction.on_commit(lambda:send_event_creation_notification_task.delay(event.id))
            
            return Response(success_response(data=serializer.data), status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EventDetailAPIView(APIView):
    """
    GET /api/events/<event_id>/
    Fetch a single event by its ID.
    Includes full event details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        try:
            # Fetch event or return 404
            event = get_object_or_404(
                Event.objects.select_related('host'),
                id=event_id,
                status='published'
            )

            # Serialize the event
            serializer = EventDetailSerializer(event, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
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
            serializer = EventAttendanceSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            attendance=serializer.save()
            # transaction.on_commit(lambda:send_event_rsvp_notification_task.delay(attendance.id))
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, event_id):
        try:
            event_attendance = EventAttendance.objects.select_related('profile').filter(id=event_id)
            serializer = EventAttendanceSerializer(event_attendance, many=True, context={'request': request})
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
            serializer = EventAttendanceSerializer(attendance, data=data, partial=True, context={'request': request})
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
                            
            serializer = EventSummarySerializer(upcoming_events, many=True, context={'request': request})
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
            media=serializer.save()
            transaction.on_commit(lambda:send_event_media_notification_task.delay(event.id,profile.id,media.id))
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
            media_qs = EventMedia.objects.filter(event=event, is_active=True).order_by('-is_pinned', '-uploaded_at')
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


class EventCommentCreateAPIView(APIView):
    """
    POST /api/events/<event_id>/comments/
    Allows a logged-in user to add a comment (or reply) to an event.
    Request:
    {
        "content": "This event looks amazing!",
        "parent": 5   # Optional, if replying to another comment
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            # Ensure event exists
            event = get_object_or_404(Event, id=event_id)
            profile = get_user_profile(request.user)

            # Inject required fields into request data
            data = request.data.copy()
            data['event'] = event.id

            # Optional: validate parent comment
            parent_id = data.get("parent")
            if parent_id:
                parent_comment = EventComment.objects.filter(id=parent_id, event=event).first()
                if not parent_comment:
                    return Response(error_response("Invalid parent comment."),
                                    status=status.HTTP_400_BAD_REQUEST)

            # Initialize serializer
            serializer = EventCommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            # Save the comment
            comment = serializer.save(profile=profile, event=event)
            transaction.on_commit(lambda: shared_event_comment_notification_task.delay(event.id, profile.id, comment.id))

            return Response(success_response(EventCommentSerializer(comment).data),
                            status=status.HTTP_201_CREATED)
            
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParentEventCommentListAPIView(APIView, PaginationMixin):
    """
    GET /api/events/<event_id>/comments/
    Lists all top-level comments for an event (no nested replies, just `has_replies` flag).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        try:
            event = get_object_or_404(Event, id=event_id)

            # Fetch top-level comments efficiently
            comments = EventComment.objects.select_related('profile', 'parent').filter(
                        event=event, parent__isnull=True
                    ) .order_by('created_at')

            # Apply pagination
            paginated_comments = self.paginate_queryset(comments, request)
            serializer = EventCommentListSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChildEventCommentListAPIView(APIView, PaginationMixin):
    """
    GET /api/events/<event_id>/comments/
    Lists all top-level comments for an event (no nested replies, just `has_replies` flag).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id, parent_id):
        try:
            event = get_object_or_404(Event, id=event_id)

            # Fetch top-level comments efficiently
            comments = EventComment.objects.select_related('profile', 'parent').filter(
                        event=event, parent__id=parent_id
                    ) .order_by('created_at')

            # Apply pagination
            paginated_comments = self.paginate_queryset(comments, request)
            serializer = EventCommentListSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaPinStatusAPIView(APIView):
    """
    PATCH /api/events/<event_id>/media/<media_id>/pin/
    Allows the event owner or org member to pin/unpin a media item.
    Request:
    {
        "is_pinned": true
    }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, event_id, media_id):
        try:
            # Validate event & media
            event = get_object_or_404(Event, id=event_id)
            media = get_object_or_404(EventMedia, id=media_id, event=event)
            profile = get_user_profile(request.user)

            # Check permission
            if not is_owner_or_org_member(event.host, request.user):
                return Response(
                    error_response("You do not have permission to update this media."),
                    status=status.HTTP_403_FORBIDDEN
                )

            # Validate input
            is_pinned = request.data.get("is_pinned")
            if is_pinned is None:
                return Response(error_response("Missing 'is_pinned' field."),
                                status=status.HTTP_400_BAD_REQUEST)

            # Update field
            media.is_pinned = bool(is_pinned)
            media.save(update_fields=["is_pinned"])

            return Response(success_response({
                "id": media.id,
                "event": event.id,
                "file": media.file.url,
                "is_pinned": media.is_pinned
            }), status=status.HTTP_200_OK)

        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PopularEventsAPIView(APIView, PaginationMixin):
    """
    GET /api/events/promoted/
    Returns a list of events promoted for homepage carousel based on popularity.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            now = timezone.now()

            # Filter events: published & upcoming
            events_qs = Event.objects.filter(
                status=EventStatus.PUBLISHED,
                start_datetime__gte=now
            ).annotate(
                annotated_attendee_count=Count('attendees', distinct=True),
                comment_count=Count('comments', distinct=True),
                media_count=Count('media', distinct=True)
            ).annotate(
                popularity_score=F('annotated_attendee_count') + F('comment_count') + F('media_count')
            ).order_by('-popularity_score', 'start_datetime')  # Most popular first
            
            higher_popular_events = events_qs.filter(  
                Q(annotated_attendee_count__gte=100) |
                Q(comment_count__gte=50) | 
                Q(media_count__gte=20)
            )
            if higher_popular_events:
                popular_events = higher_popular_events
            else:
                popular_events = events_qs
                
            paginated_response = self.paginate_queryset(popular_events, request)
            serializer = EventSummarySerializer(paginated_response, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateEventMediaCommentAPIView(APIView):
    """
    API view to create comments on event media
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, event_media_id):
        try:
            # Ensure event exists
            event_media = get_object_or_404(EventMedia, id=event_media_id)
            profile = get_user_profile(request.user)

            # Inject required fields into request data
            data = request.data.copy()
            data['event_media'] = event_media.id

            # Optional: validate parent comment
            parent_id = data.get("parent")
            if parent_id:
                parent_comment = EventMediaComment.objects.filter(id=parent_id, event_media=event_media).first()
                if not parent_comment:
                    return Response(error_response("Invalid parent comment."),
                                    status=status.HTTP_400_BAD_REQUEST)

            # Initialize serializer
            serializer = EventMediaCommentSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            # Save the comment
            comment = serializer.save(profile=profile, event_media=event_media)

            return Response(success_response(EventCommentSerializer(comment).data),
                            status=status.HTTP_201_CREATED)
            
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParentEventMediaCommentsAPIView(APIView, PaginationMixin):
    """
    API to get the list of all parent comments of an event media
    """
    
    def get(self, request, evnet_media_id):
        try:
            comments = EventMediaComment.objects.select_related('profile', 'parent').filter(
                event_media__id=evnet_media_id, parent__isnull=True)
            
            paginated_response = self.paginate_queryset(comments, request)
            serializer = EventMediaCommentSerializer(paginated_response, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
            
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChildEventMediaCommentListAPIView(APIView, PaginationMixin):
    """
    API to get the list of all child comments of an event media
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_media_id, parent_id):
        try:
            event_media = get_object_or_404(EventMedia, id=event_media_id)

            comments = EventMediaComment.objects.select_related('profile', 'parent').filter(
                        event_media=event_media.id, parent__id=parent_id
                    ) .order_by('created_at')

            paginated_comments = self.paginate_queryset(comments, request)
            serializer = EventMediaCommentSerializer(paginated_comments, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))
        
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)