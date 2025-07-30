# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
import openpyxl
from datetime import datetime, time


# Django imports
from django.utils import timezone
from django.db.models import Q, Count, F, IntegerField, ExpressionWrapper
from django.db.models.functions import ExtractHour, Coalesce
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.db import IntegrityError

# Local imports
from event.serializers import (
    EventCreateSerializer, EventListSerializer, EventAttendanceSerializer, EventSerializer, EventSummarySerializer, EventMediaSerializer, 
    EventCommentSerializer, EventCommentListSerializer, EventMediaCommentSerializer, EventDetailSerializer, EventSerializer,
    EventUpdateSerializer,EventMediaLikeSerializer,EventMediaCommentLikeSerializer, EventActivityLogSerializer
)
from event.models import (
    Event, EventAttendance, EventMedia, EventComment, EventMediaComment, EventMediaLike,EventMediaCommentLike, EventActivityLog
)
from event.choices import (
    EventStatus, AttendanceStatus, EventActivityType
)
from event.utils import (
    handle_event_hashtags, is_host_or_cohost, get_event_by_id_or_slug,handle_event_share
)
from notification.task import (
    send_event_creation_notification_task, send_event_rsvp_notification_task, send_event_media_notification_task, 
    shared_event_media_comment_notification_task,send_event_share_notification_task
)
from profiles.models import (
    Profile
)
from profiles.serializers import (
    ProfileListSerializer
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
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            data=request.data

            serializer = EventCreateSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            event = serializer.save(host=profile)
            
            try:
                transaction.on_commit(lambda:send_event_creation_notification_task.delay(event.id))
            except:
                pass
            
            handle_event_hashtags(event)
            
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

    def get(self, request, event_id=None, slug=None):
        try:
            if event_id:
                event = get_object_or_404(
                    Event.objects.select_related('host'),
                    id=event_id,
                    status='published'
                )
            elif slug:
                event = get_object_or_404(
                    Event.objects.select_related('host'),
                    slug=slug,
                    status='published'
                )
            else:
                raise ValueError("Either profile_id or username is required.")

            # Serialize the event
            serializer = EventDetailSerializer(event, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
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


class EventAttendacneAPIView(APIView, PaginationMixin):
    """
    API for Event RSVP
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            data = request.data
            event_id = data.get('event')
            status_value = data.get('status', AttendanceStatus.INTERESTED)

            if not event_id:
                return Response(error_response("Event ID is required"), status=status.HTTP_400_BAD_REQUEST)

            # Check event settings
            event = Event.objects.get(id=event_id)
            
            exisiting = EventAttendance.objects.filter(profile=profile, event=event)
            if exisiting:
                return Response(success_response("RSVP already submitted"), status=status.HTTP_200_OK)
            
            if event.aprove_attendees and status_value==AttendanceStatus.INTERESTED:
                # Force RSVP to pending regardless of requested status
                status_value = AttendanceStatus.PENDING

            data['profile'] = profile.id
            data['status'] = status_value

            serializer = EventAttendanceSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            attendance = serializer.save()
            try:
                transaction.on_commit(lambda:send_event_rsvp_notification_task.delay(attendance.id))
            except:
                pass
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        
        except Event.DoesNotExist:
            return Response(error_response("Event not found"), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, event_id):
        try:
            event_attendance = EventAttendance.objects.select_related('profile').filter(event__id=event_id)
            
            status_filter = request.query_params.get('status')
            if status_filter:
                event_attendance = event_attendance.filter(status=status_filter.lower())
                
            paginated_qs = self.paginate_queryset(event_attendance, request)
            serializer = EventAttendanceSerializer(paginated_qs, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
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
            
            if status_value not in [AttendanceStatus.INTERESTED, AttendanceStatus.NOT_INTERESTED]:
                return  Response(error_response("Invalid status value"), status=status.HTTP_400_BAD_REQUEST)
            
            event = Event.objects.get(id=event_id)
            if event.aprove_attendees and status_value==AttendanceStatus.INTERESTED:
                # Force RSVP to pending regardless of requested status
                status_value = AttendanceStatus.PENDING

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
            
            host_or_cohost = is_host_or_cohost(event, profile)

            # Permission check
            if event.allow_public_media == False and not host_or_cohost:
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
            media=serializer.save(uploaded_by_host=host_or_cohost)
            try:
                transaction.on_commit(lambda:send_event_media_notification_task.delay(event.id,profile.id,media.id))
            except:
                pass
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
            media_qs = EventMedia.objects.select_related('uploaded_by').filter(event=event, is_active=True).order_by('-is_pinned', '-uploaded_at')
            uploaded_by_host = request.query_params.get('uploaded_by_host')
            
            if uploaded_by_host:
                is_host = uploaded_by_host.strip().lower() == 'true'
                media_qs = media_qs.filter(uploaded_by_host=is_host)
                
                
            serializer = EventMediaSerializer(media_qs, many=True)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)

        except Event.DoesNotExist:
            return Response(error_response("Event not found."), status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class EventMediaDetailAPIView(APIView):
    """
    GET /api/events/media/<media_id>/
    Returns a single media item for a given event.
    """
    def get(self,request,media_id):
        try:
            media=EventMedia.objects.get(id=media_id,is_active=True)

            serializer=EventMediaSerializer(media)
            return Response(success_response(serializer.data),status=status.HTTP_200_OK)
        except Event.DoesNotExist:
            return Response(error_response("Event not found."), status=status.HTTP_404_NOT_FOUND)

        except EventMedia.DoesNotExist:
            return Response(error_response("Media not found for this event."), status=status.HTTP_404_NOT_FOUND)

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

            if not is_host_or_cohost(event, profile):
                return Response(error_response("You do not have permission to update this event."), status=status.HTTP_403_FORBIDDEN)

            data = request.data.copy()
            data['host'] = event.host.id  # preserve original host

            serializer = EventUpdateSerializer(event, data=data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            handle_event_hashtags(event)

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
                    ).order_by('-created_at')

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
                    ).order_by('-created_at')

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
                annotated_media_count=Count('media', distinct=True)
            ).annotate(
                popularity_score=F('annotated_attendee_count') + F('comment_count') + F('annotated_media_count')
            ).order_by('-popularity_score', 'start_datetime')
            
            higher_popular_events = events_qs.filter(
                Q(annotated_attendee_count__gte=100) |
                Q(comment_count__gte=50) | 
                Q(annotated_media_count__gte=20)
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
            try:
                transaction.on_commit(lambda: shared_event_media_comment_notification_task.delay(event_media.id, profile.id, comment.id))
            except:
                pass

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


class MyHostedEventsAPIView(APIView, PaginationMixin):
    """
    GET /api/events/my-hosted/

    Returns all events where the logged-in user's profile is the host or co-host.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get profile of logged-in user
            profile = get_user_profile(request.user)
            if not profile:
                return Response(error_response("Profile not found."), status=status.HTTP_404_NOT_FOUND)

            # Fetch events where user is host or co-host
            events = Event.objects.filter(
                (Q(host=profile) | Q(co_hosts=profile))
            ).order_by('-start_datetime')

            # Paginate
            paginated_events = self.paginate_queryset(events, request)
            serializer = EventDetailSerializer(paginated_events, many=True, context={'request': request})

            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SuggestedEventsAPIView(APIView, PaginationMixin):
    """
    GET /api/events/suggestions/
    Returns upcoming suggested events based on tags of events the user is attending,
    paginated and ordered by most attendees.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = get_user_profile(request.user)

            # 1. Get attended events
            attended_event_ids = EventAttendance.objects.filter(
                profile=profile
            ).values_list('event_id', flat=True)

            # 2. Get related tag IDs
            tag_ids = Event.objects.filter(
                Q(id__in=attended_event_ids) | Q(host=profile)
            ).values_list('tags', flat=True)

            # 3. Get upcoming events matching tags, exclude already attended
            suggested_events = Event.objects.filter(
                tags__in=tag_ids,
                start_datetime__gte=timezone.now()
            ).exclude(
                Q(id__in=attended_event_ids) | Q(host=profile)
            ).annotate(
                num_attendees=Count('attendees')
            ).order_by('-num_attendees').distinct()

            # 4. Paginate results
            paginated_events = self.paginate_queryset(suggested_events, request)
            serializer = EventSerializer(paginated_events, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)


    

class AddCoHostsAPIView(APIView):
    """
    POST /api/events/<event_id>/add-cohosts/
    Allows the event host to add multiple co-hosts.

    Request:
    {
        "co_host_ids": [5, 6, 7]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            profile = get_user_profile(request.user)
            event = get_object_or_404(Event, id=event_id)

            # Only host can add co-hosts
            if event.host != profile:
                return Response(
                    error_response("Only the host can add co-hosts."),
                    status=status.HTTP_403_FORBIDDEN
                )

            co_host_ids = request.data.get("co_host_ids", [])
            
            if not isinstance(co_host_ids, list):
                raise ValueError('co_host_ids must be an instance of list') 
            
            if not co_host_ids:
                return Response(
                    error_response("Provide at least one co-host ID."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Exclude invalid cases
            valid_co_hosts = Profile.objects.filter(id__in=co_host_ids).exclude(id=profile.id)

            if not valid_co_hosts.exists():
                return Response(
                    error_response("No valid co-hosts found."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            event.co_hosts.add(*valid_co_hosts)

            return Response(
                success_response({
                    "event_id": event.id,
                    "added_co_hosts": list(valid_co_hosts.values_list("id", flat=True))
                }),
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveCoHostAPIView(APIView):
    """
    POST /api/events/<event_id>/remove-cohost/
    Removes a co-host from the event.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            profile = get_user_profile(request.user)
            event = get_object_or_404(Event, id=event_id)

            if event.host != profile:
                return Response(
                    error_response("Only the host can remove co-hosts."),
                    status=status.HTTP_403_FORBIDDEN
                )

            co_host_id = request.data.get("co_host_id")
            if not co_host_id:
                return Response(
                    error_response("Co-host ID is required."),
                    status=status.HTTP_400_BAD_REQUEST
                )

            event.co_hosts.remove(co_host_id)

            return Response(
                success_response({"event_id": event.id, "removed_co_host": co_host_id}),
                status=status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaLikeAPIView(APIView, PaginationMixin):
    """
    GET /api/event-media/likes/grouped/
    Returns paginated event media with their likes grouped under each media item.
    """
    def get(self, request):
        try:

            # Get all media that has likes
            media_ids = EventMediaLike.objects.values_list('event_media_id', flat=True).distinct()
            media_queryset = EventMedia.objects.filter(id__in=media_ids).order_by('-uploaded_at')

            # Paginate media queryset
            paginated_media = self.paginate_queryset(media_queryset, request)

            # Build grouped data
            grouped_results = []
            for media in paginated_media:
                media_data = EventMediaSerializer(media, context={'request': request}).data
                likes = EventMediaLike.objects.filter(event_media=media)
                like_data = EventMediaLikeSerializer(likes, many=True, context={'request': request}).data
                grouped_results.append({
                    'event_media': media_data,
                    'likes': like_data
                })

            return self.get_paginated_response(grouped_results)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            media_id = request.data.get("event_media")

            if not profile or not media_id:
                return Response(error_response("Both profile and event_media are required."), status=status.HTTP_400_BAD_REQUEST)

            media = EventMedia.objects.filter(id=media_id).first()
            if not media:
                return Response(error_response("EventMedia not found."), status=status.HTTP_404_NOT_FOUND)

            existing_like = EventMediaLike.objects.filter(profile=profile, event_media_id=media_id).first()

            with transaction.atomic():
                if existing_like:
                    existing_like.delete()
                    media.like_count = max((media.like_count or 1) - 1, 0)
                    media.save(update_fields=["like_count"])
                    return Response({"message": "Disliked (like removed)."}, status=status.HTTP_200_OK)
                else:
                    like = EventMediaLike.objects.create(
                        profile=profile,
                        event_media=media
                    )
                    media.like_count = (media.like_count or 0) + 1
                    media.save(update_fields=["like_count"])

                    # Return serialized data
                    serializer = EventMediaLikeSerializer(like)
                    return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class EventMediaLikeDetailAPIView(APIView):
    """
    Authenticated Like Detail View

    GET: Retrieve like details (only if owned)
    PUT: Update like (only if owned)
    DELETE: Remove like (only if owned)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, profile):
        try:
            return EventMediaLike.objects.get(pk=pk, profile=profile)
        except EventMediaLike.DoesNotExist:
            raise Http404("Like not found or not owned by you.")

    def get(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            like = self.get_object(pk, profile)
            serializer = EventMediaLikeSerializer(like)
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def delete(self, request, pk):
        try:
            profile = get_user_profile(request.user)
            like = self.get_object(pk, profile)
            media = like.event_media

            like.delete()

            if media.like_count:
                media.like_count = max(0, media.like_count - 1)
                media.save(update_fields=['like_count'])

            return Response({"message": "Like deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class EventMediaLikesByIdAPIView(APIView, PaginationMixin):
    """
    GET /api/event-media/<id>/likes/
    Returns a single event media with its likes (paginated).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            media = EventMedia.objects.filter(id=id).first()
            if not media:
                return Response({"status": False, "message": "EventMedia not found."}, status=404)


            likes_queryset = EventMediaLike.objects.filter(event_media=media).order_by('-created_at')  # Optional ordering

            # Paginate the likes
            paginated_likes = self.paginate_queryset(likes_queryset, request)
            serialized_likes = EventMediaLikeSerializer(paginated_likes, many=True, context={'request': request}).data

            return self.get_paginated_response({
                "status": True,
                "likes": serialized_likes
            })

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=500)

       
class EventListByHostOrCoHostAPIView(APIView, PaginationMixin):
    """
    GET /api/events/by-user/<username>/
    Returns events where the given username is host or co-host.
    """
    def get(self, request, username):
        try:
            try:
                profile = Profile.objects.get(username=username)
            except Profile.DoesNotExist:
                return Response({
                    "status": False,
                    "message": "Profile with this username does not exist."
                }, status=404)

            events = Event.objects.filter(
                Q(host=profile) | Q(co_hosts=profile),
                status='published'
            ).distinct()

            paginated = self.paginate_queryset(events, request)
            serializer = EventDetailSerializer(paginated, many=True, context={'request': request})
            return self.get_paginated_response(success_response(serializer.data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)


class ApproveRSVPAPIView(APIView):
    """
    Allows the host or co-host of an event to approve or reject a user's RSVP.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            profile = get_user_profile(request.user)
            attendance_id = request.data.get('attendance_id')
            action = request.data.get('action')

            if not attendance_id or action not in ['approve', 'reject']:
                return Response(error_response("Invalid parameters"), status=status.HTTP_400_BAD_REQUEST)

            attendance = EventAttendance.objects.select_related('event', 'profile').get(id=attendance_id)
            event = attendance.event

            # Check if the user is authorized (host or co-host)
            if not is_host_or_cohost(event, profile):
                return Response(
                    error_response("You are not authorized to approve or reject RSVPs for this event."),
                    status=status.HTTP_403_FORBIDDEN
                )

            # Perform action
            if action == 'approve':
                attendance.status = AttendanceStatus.INTERESTED
            else:
                attendance.status = AttendanceStatus.DECLINED

            attendance.save()

            return Response(success_response({
                "profile": attendance.profile.username,
                "event": event.title,
                "status": attendance.status
            }), status=status.HTTP_200_OK)

        except EventAttendance.DoesNotExist:
            return Response(error_response("Attendance record not found"), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaCommentLikeToggleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = get_user_profile(request.user)
            comment_id = request.data.get("comment_id")

            if not profile or not comment_id:
                return Response(error_response("Both profile and comment_id are required."), status=status.HTTP_400_BAD_REQUEST)

            comment = EventMediaComment.objects.filter(id=comment_id).first()
            if not comment:
                return Response(error_response("Comment not found."), status=status.HTTP_404_NOT_FOUND)

            existing_like = EventMediaCommentLike.objects.filter(profile=profile, eventmediacomment_id=comment_id).first()

            with transaction.atomic():
                if existing_like:
                    existing_like.delete()
                    comment.like_count = max((comment.like_count or 1) - 1, 0)
                    comment.save(update_fields=["like_count"])
                    return Response({"message": "Disliked (like removed)."}, status=status.HTTP_200_OK)
                else:
                    like = EventMediaCommentLike.objects.create(
                        profile=profile,
                        event_media_comment=comment
                    )
                    comment.like_count = (comment.like_count or 0) + 1
                    comment.save(update_fields=["like_count"])

                    serializer = EventMediaCommentLikeSerializer(like)
                    return Response(success_response(serializer.data), status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventMediaCommentLikeListAPIView(APIView, PaginationMixin):
    """
    GET /api/eventmediacomment/<comment_id>/likes/
    Returns a paginated list of likes on a specific comment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, comment_id):
        try:
            comment = EventMediaComment.objects.filter(id=comment_id).first()
            if not comment:
                return Response(error_response("Comment not found."), status=404)

            likes_qs = EventMediaCommentLike.objects.filter(event_media_comment=comment).order_by('-created_at')
            paginated_likes = self.paginate_queryset(likes_qs, request)
            serializer = EventMediaCommentLikeSerializer(paginated_likes, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=500)


class GetCoHostListAPIView(APIView, PaginationMixin):
    """
    gets the list of all co hosts in an event
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, event_id=None, event_slug=None):
        try:
            event = get_event_by_id_or_slug(event_id, event_slug)
            co_hosts = event.co_hosts.all()
            
            paginaged_qs = self.paginate_queryset(co_hosts, request)
            serializer = ProfileListSerializer(paginaged_qs, many=True)
            return self.get_paginated_response(serializer.data)
        except ValueError as e:
            return Response(error_response(str(e), status=status.HTTP_400_BAD_REQUEST))
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
            

class EventViewActivityAPIView(APIView):
    """
    POST /api/events/<event_id>/view/
    Records a 'view' activity for the logged-in user (only once per event).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        try:
            profile = get_user_profile(request.user)
            event = Event.objects.get(id=event_id)

            # Check if this user has already viewed this event
            already_viewed = EventActivityLog.objects.filter(
                profile=profile,
                event=event,
                activity_type=EventActivityType.VIEW
            ).exists()

            if already_viewed:
                return Response(
                    {"detail": "You have already viewed this event."},
                    status=status.HTTP_200_OK
                )

            # Increment the view count
            event.view_count = F('view_count') + 1
            event.save(update_fields=['view_count'])

            # Log the view activity
            data = {
                'event': event.id,
                'activity_type': EventActivityType.VIEW,
            }

            serializer = EventActivityLogSerializer(data=data)
            if serializer.is_valid():
                serializer.save(profile=profile)
                event.refresh_from_db(fields=['view_count'])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EventShareActivityAPIView(APIView):
    """
    POST /api/events/<event_id>/share_count/
    Records a 'share_count' activity for the logged-in user (only once per event).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
            try:
                profile = get_user_profile(request.user)
                event = Event.objects.get(id=event_id)

                status_msg, success = handle_event_share(profile, event)

                if not success:
                    return Response({"detail": status_msg}, status=status.HTTP_200_OK)

                event.refresh_from_db(fields=['share_count'])

                return Response({
                    "event_id": event.id,
                    "share_count": event.share_count,
                    "detail": status_msg
                }, status=status.HTTP_201_CREATED)

            except Event.DoesNotExist:
                return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class EventAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)

            # Reach
            reach = EventActivityLog.objects.filter(
                event=event, activity_type=EventActivityType.VIEW
            ).values('profile').distinct().count()
            attendance_stats = (
                EventAttendance.objects
                .filter(event=event)
                .values('status')
                .annotate(count=Count('id'))
            )
            rsvp_counts = {status: 0 for status in AttendanceStatus.values}
            for entry in attendance_stats:
                status = entry["status"]
                count = entry["count"]
                rsvp_counts[status] = count
            # RSVP Rate
            rsvped_users = EventAttendance.objects.filter(
                event=event
            ).values('profile').distinct().count()
            rsvp_rate = (rsvped_users / reach * 100) if reach > 0 else 0

            # Peak Engagement Time
            peak_hour = EventActivityLog.objects.filter(
                event=event,
                activity_type__in=[EventActivityType.VIEW, EventActivityType.COMMENT]
            ).annotate(hour=ExtractHour('timestamp')).values('hour').annotate(
                total=Count('id')
            ).order_by('-total').first()

            # Top Commenters
            top_commenters = EventComment.objects.filter(
                event=event
            ).values('profile__username').annotate(
                total_comments=Count('id')
            ).order_by('-total_comments')[:5]

            return Response({
                "reach": reach,
                "rsvp_counts": rsvp_counts,
                "rsvp_rate": round(rsvp_rate, 2),
                "peak_engagement_hour": peak_hour,
                "top_commenters": list(top_commenters)
            })

        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=404)



class ShareEventWithProfilesAPIView(APIView):
    """
    POST /api/events/share/
    Shares an event with multiple profiles (excluding host/co-hosts).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_profile = get_user_profile(request.user)
            data = request.data

            event_id = data.get('event')
            profile_ids = set(data.get('profiles', []))
            custom_message = data.get('message')

            if not event_id:
                return Response(error_response("Event ID is required"), status=status.HTTP_400_BAD_REQUEST)
            if not profile_ids or not isinstance(profile_ids, set | list):
                return Response(error_response("Profiles must be a list"), status=status.HTTP_400_BAD_REQUEST)

            try:
                event = Event.objects.select_related('host').prefetch_related('co_hosts').get(id=event_id)
            except Event.DoesNotExist:
                return Response(error_response("Event not found"), status=status.HTTP_404_NOT_FOUND)

            responses = []
            errors = []
            share_counter = 0

            for pid in profile_ids:
                try:
                    profile = Profile.objects.get(id=pid)
                    status_msg, success = handle_event_share(profile, event, message=custom_message, sender_id=user_profile.id)

                    if success:
                        share_counter += 1

                    responses.append({
                        "profile_id": pid,
                        "status": status_msg
                    })

                except Exception as notify_error:
                    errors.append({
                        "profile_id": pid,
                        "error": str(notify_error)
                    })

            return Response({
                "shared_count": share_counter,
                "already_shared": len([r for r in responses if r["status"] == "Already shared"]),
                "skipped_count": len([r for r in responses if r["status"].startswith("Skipped")]),
                "failure_count": len(errors),
                "shared": responses,
                "errors": errors
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class PublicEventDetailAPIView(APIView):
    """
    GET /api/events/<event_id>/
    Fetch a single event by its ID.
    Includes full event details.
    """
    # permission_classes = [AllowAny]

    def get(self, request, event_id=None, slug=None):
        try:
            if event_id:
                event = get_object_or_404(
                    Event.objects.select_related('host'),
                    id=event_id,
                    status='published'
                )
            elif slug:
                event = get_object_or_404(
                    Event.objects.select_related('host'),
                    slug=slug,
                    status='published'
                )
            else:
                raise ValueError("Either profile_id or username is required.")

            # Serialize the event
            serializer = EventDetailSerializer(event, context={'request': request})
            return Response(success_response(serializer.data), status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        

class DownloadEventAttendanceExcel(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

        profile = get_user_profile(request.user)  
        if profile != event.host and profile not in event.co_hosts.all():
            return Response({"error": "Only host or co-host can download attendance"}, status=status.HTTP_403_FORBIDDEN)

        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Attendance for {event.title}"

        # Add headers
        ws.append(["ID", "Username", "Email", "Status", "Joined At"])

        # Order by status
        attendance_qs = EventAttendance.objects.filter(event=event).select_related("profile").order_by("status")

        for att in attendance_qs:
            ws.append([
                att.id,
                att.profile.username,
                att.profile.user.email,
                att.status,
                att.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(att, 'created_at') else ''
            ])

        # Return Excel file
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"{event.title}_attendance.xlsx".replace(" ", "_")
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response



class FilterEventListAPIView(APIView, PaginationMixin):
    def get(self, request):
        try:
            queryset = Event.objects.all()
            filters = Q()

            # Filters
            title = request.GET.get('title')
            upcoming = request.GET.get('upcoming')
            past = request.GET.get('past')
            is_online = request.GET.get('is_online')
            is_free = request.GET.get('is_free')
            address = request.GET.get('address')
            city_name = request.GET.get('city')
            state_name = request.GET.get('state')
            country_name = request.GET.get('country')
            host_name = request.GET.get('host_name')
            co_host_name = request.GET.get('co_host_name')
            tag = request.GET.get('tag')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            ordering = request.GET.get('ordering')

            if title:
                filters &= Q(title__icontains=title)
            if is_online is not None:
                filters &= Q(is_online=is_online.lower() == 'true')
            if is_free is not None:
                filters &= Q(is_free=is_free.lower() == 'true')
            if address:
                filters &= Q(address__icontains=address)
            if city_name:
                filters &= Q(city__name__icontains=city_name)
            if state_name:
                filters &= Q(state__name__icontains=state_name)
            if country_name:
                filters &= Q(country__name__icontains=country_name)
            if host_name:
                filters &= Q(host__username__icontains=host_name)
            if co_host_name:
                filters &= Q(co_hosts__username__icontains=co_host_name)
            if tag:
                filters &= Q(tags__name__icontains=tag)
            if upcoming and upcoming.lower() == 'true':
                filters &= Q(start_datetime__gt=timezone.now())
            if past and past.lower() == 'true':
                filters &= Q(end_datetime__lt=timezone.now())

            # Start and end date filter
            if start_date and end_date:
                try:
                    start_date = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                    end_date = timezone.make_aware(datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), time.max))
                    filters &= Q(start_datetime__gte=start_date, end_datetime__lte=end_date)
                except ValueError:
                    return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            queryset = queryset.filter(filters)

            # Annotate attendance
            queryset = queryset.annotate(
                attendance_count=Count('eventattendance', distinct=True)
            )

            # Popularity
            queryset = queryset.annotate(
                popularity=ExpressionWrapper(
                    Coalesce(F('view_count'), 0) +
                    Coalesce(F('share_count'), 0) +
                    Coalesce(F('attendance_count'), 0),
                    output_field=IntegerField()
                )
            )

            # Ordering
            if ordering == 'popular':
                queryset = queryset.order_by('-popularity')
            elif ordering == 'date':
                queryset = queryset.order_by('start_datetime')
            elif ordering == 'latest':
                queryset = queryset.order_by('-id')

            queryset = queryset.distinct()
            paginated_queryset = self.paginate_queryset(queryset, request)
            serializer = EventDetailSerializer(paginated_queryset, many=True)
            return self.get_paginated_response(serializer.data)

        except ValueError as e:
            return Response(error_response(str(e)), status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            return Response(error_response(str(e)), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        


