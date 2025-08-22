# Django imports
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

# Local imports
from core.models import (
    Country, State, City, UpcomingFeature, WeeklyChallenge
)
from core.serializers import (
    CountrySerializer, StateSerializer, CitySerializer, UpcomingFeatureSerializer, WeeklyChallengeSerializer
)
from core.services import success_response, error_response
from core.pagination import PaginationMixin
from core.models import (
    HashTag
)
from core.serializers import (
    HashTagSerializer
)
from profiles.models import Profile
from user.models import CustomUser


class LocationHierarchyAPIView(APIView, PaginationMixin):
    """
    GET /api/locations/?country_id=<id>&state_id=<id>
    """
    def get(self, request):
        try:
            country_id = request.query_params.get('country_id')
            state_id = request.query_params.get('state_id')

            if state_id:
                cities = City.objects.filter(state_id=state_id).order_by('name')
                paginated = self.paginate_queryset(cities, request)
                serializer = CitySerializer(paginated, many=True)
                return self.get_paginated_response(serializer.data)

            elif country_id:
                states = State.objects.filter(country_id=country_id).order_by('name')
                if states.exists():
                    paginated = self.paginate_queryset(states, request)
                    serializer = StateSerializer(paginated, many=True)
                    return self.get_paginated_response(serializer.data)
                else:
                    cities = City.objects.filter(country_id=country_id, state__isnull=True).order_by('name')
                    paginated = self.paginate_queryset(cities, request)
                    serializer = CitySerializer(paginated, many=True)
                    return self.get_paginated_response(serializer.data)

            else:
                countries = Country.objects.all().order_by('name')
                paginated = self.paginate_queryset(countries, request)
                serializer = CountrySerializer(paginated, many=True)
                return self.get_paginated_response(serializer.data)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CountrySearchView(APIView, PaginationMixin):
    def get(self, request):
        try:
            query = request.query_params.get('q', '')
            countries = Country.objects.filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            ).order_by('name')

            paginated = self.paginate_queryset(countries, request)
            serializer = CountrySerializer(paginated, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StateSearchView(APIView, PaginationMixin):
    def get(self, request):
        try:
            query = request.query_params.get('q', '')
            country_id = request.query_params.get('country')

            states = State.objects.filter(name__icontains=query)
            if country_id:
                states = states.filter(country_id=country_id)
            states = states.order_by('name')

            paginated = self.paginate_queryset(states, request)
            serializer = StateSerializer(paginated, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CitySearchView(APIView, PaginationMixin):
    def get(self, request):
        try:
            query = request.query_params.get('q', '')
            country_id = request.query_params.get('country')
            state_id = request.query_params.get('state')

            cities = City.objects.filter(name__icontains=query)
            if state_id:
                cities = cities.filter(state_id=state_id)
            if country_id:
                cities = cities.filter(country_id=country_id)
            cities = cities.order_by('name')

            paginated = self.paginate_queryset(cities, request)
            serializer = CitySerializer(paginated, many=True)
            return self.get_paginated_response(serializer.data)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WeeklyChallengeAPIView(APIView, PaginationMixin):
    
    def get(self, request):
        try:
            today = timezone.now().date()
            weekly_challanges = WeeklyChallenge.objects.filter(
                start_date__lte=today, end_date__gte=today, is_active=True
            ).order_by('-start_date')
            paginated = self.paginate_queryset(weekly_challanges, request)
            serializer = WeeklyChallengeSerializer(paginated, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpcomingFeatureAPIView(APIView, PaginationMixin):
    """             
    GET /api/upcoming-features/
    Returns a list of upcoming features that are currently active.  
        """
    
    def get(self, request):
        try:
            features = UpcomingFeature.objects.filter(status=True).order_by('-created_at')
            paginated = self.paginate_queryset(features, request)
            serializer = UpcomingFeatureSerializer(paginated, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)   
    
    def post(self, request):
        try:
            serializer = UpcomingFeatureSerializer(data=request.data)
            if serializer.is_valid():
                feature = serializer.save()
                return Response(UpcomingFeatureSerializer(feature).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HashTagSearchAPIView(APIView, PaginationMixin):
    """
    Search hashtags by partial name.
    """
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(error_response("Missing 'q' query parameter."), status=status.HTTP_400_BAD_REQUEST)
        
        hashtags = HashTag.objects.filter(name__icontains=query).order_by("name")
        paginated_qs = self.paginate_queryset(hashtags, request)
        serializer = HashTagSerializer(paginated_qs, many=True)
        return self.get_paginated_response(serializer.data)


from datetime import timedelta
from django.utils.timezone import now

from user.models import CustomUser
from group.models import Group
from event.models import Event, EventAttendance
from post.models import Post
from notification.models import Notification
from django.db.models import Count, Avg, Max, Min,Sum, F
from rest_framework.views import APIView
import datetime
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_datetime, parse_date
from event.choices import EventStatus, AttendanceStatus


class UserStatsView(APIView):
    def get(self, request):
        end_date = now()
        start_date = end_date - timedelta(days=7)  # default: last 7 days
        data = {
            "total": CustomUser.objects.count(),
            # If you added date_joined in CustomUser:
            # "new": CustomUser.objects.filter(date_joined__gte=start_date).count(),
        }
        return Response(data)


# --- Groups ---
class GroupStatsView(APIView):
    def get(self, request):
        start_date = now() - timedelta(days=7)
        groups = {
            "total": Group.objects.count(),
            "recently_active": Group.objects.filter(last_activity_at__gte=start_date).count(),
            "featured": Group.objects.filter(featured=True).count(),
            "top_by_members": list(Group.objects.order_by("-member_count")
                                   .values("name", "member_count")[:3]),
            "top_by_posts": list(Group.objects.order_by("-post_count")
                                 .values("name", "post_count")[:3]),
            "top_trending": list(Group.objects.order_by("-trending_score")
                                  .values("name", "trending_score")[:3]),
            "avg_engagement": Group.objects.aggregate(avg=Avg("avg_engagement"))["avg"] or 0.0,
        }
        return Response(groups)


# --- Events ---
class EventStatsView(APIView):
    def get(self, request):
        end_date = now()
        start_of_week = end_date - timedelta(days=end_date.weekday())
        today_events = Event.objects.filter(start_datetime__date=end_date.date(), status='published')

        events = {
            "ongoing_this_week": Event.objects.filter(start_datetime__gte=start_of_week,
                                                      start_datetime__lte=end_date,
                                                      status='published').count(),
            "upcoming_next_month": Event.objects.filter(start_datetime__gte=end_date,
                                                        start_datetime__lte=end_date + timedelta(days=30),
                                                        status='published').count(),
            "today": today_events.count(),
            "rsvp_interested_today": EventAttendance.objects.filter(event__in=today_events,
                                                                    status='INTERESTED').count(),
            "top_3_events": list(Event.objects.filter(start_datetime__gte=end_date)
                                 .order_by('-view_count')
                                 .values("title", "view_count")[:3]),
            "highest_attendee_events": list(Event.objects.annotate(attendee_count=Count('attendees'))
                                            .order_by('-attendee_count')
                                            .values("title", "attendee_count")[:3]),
        }
        return Response(events)


# --- Posts ---
class PostStatsView(APIView):
    def get(self, request):
        end_date = now()
        start_of_week = end_date - timedelta(days=end_date.weekday())
        posts_this_week = Post.objects.filter(created_at__gte=start_of_week)

        trending_post = posts_this_week.annotate(
            engagement=F("reaction_count") + F("comment_count") + F("share_count")
        ).order_by("-engagement").first()

        posts = {
            "total": Post.objects.count(),
            "highest_reached_post": Post.objects.order_by("-view_count")
                                   .values("title", "view_count").first() or {},
            "trending_post_this_week": {"title": trending_post.title if trending_post else None,
                                        "engagement": getattr(trending_post, "engagement", 0)},
            "highest_uploader_this_week": posts_this_week.values("profile__username")
                                           .annotate(total_posts=Count("id"))
                                           .order_by("-total_posts").first() or {},
            "avg_engagement_this_week": round(posts_this_week.aggregate(
                avg=Sum(F("reaction_count") + F("comment_count") + F("share_count")) / Count("id")
            )["avg"] or 0, 2),
            "top_comment_post": posts_this_week.order_by("-comment_count")
                                  .values("title", "comment_count").first() or {},
            "top_share_post": posts_this_week.order_by("-share_count")
                                .values("title", "share_count").first() or {},
            "top_like_post": posts_this_week.order_by("-reaction_count")
                               .values("title", "reaction_count").first() or {},
        }
        return Response(posts)


# --- Profiles ---
class ProfileStatsView(APIView):
    def get(self, request):
        end_date = now()
        start_of_week = end_date - timedelta(days=end_date.weekday())

        most_followed = Profile.objects.annotate(follower_total=Count("followers")) \
                                       .order_by("-follower_total").first()
        most_friends = Profile.objects.annotate(friends_total=Count("friends")) \
                                      .order_by("-friends_total").first()
        top_creator = Profile.objects.annotate(post_total=Count("posts")) \
                                     .order_by("-post_total").first()

        profiles = {
            "total": Profile.objects.count(),
            "verified": Profile.objects.filter(is_verified=True).count(),
            "active_this_week": Profile.objects.filter(last_active_at__gte=start_of_week).count(),
            "most_followed": {"username": most_followed.username if most_followed else None,
                              "followers": getattr(most_followed, "follower_total", 0)},
            "most_viewed": Profile.objects.order_by("-view_count")
                            .values("username", "view_count").first() or {},
            "top_creator": {"username": top_creator.username if top_creator else None,
                            "posts": getattr(top_creator, "post_total", 0)},
            "avg_followers": round(Profile.objects.annotate(follower_total=Count("followers"))
                                   .aggregate(avg=Avg("follower_total"))["avg"] or 0, 2),
            "most_friends": {"username": most_friends.username if most_friends else None,
                             "friends": getattr(most_friends, "friends_total", 0)},
        }
        return Response(profiles)


# --- Notifications ---
class NotificationStatsView(APIView):
    def get(self, request):
        start_date = now() - timedelta(days=7)
        notifications = {
            "sent": Notification.objects.filter(created_at__gte=start_date).count(),
            "failure_rate": 0,  # placeholder
            "retries": Notification.objects.filter(created_at__gte=start_date,
                                                   is_read__gt=0).count(),
        }
        return Response(notifications)  


class ProfileFilterOptionsView(APIView):
    """
    Returns available filter options for profiles analytics (for frontend dropdowns).
    """

    def get(self, request):
        options = {
            "profile_scope": [
                {"key": "all", "label": "All Profiles"},
                {"key": "verified", "label": "Verified Profiles"},
                {"key": "active", "label": "Active This Week"},
                {"key": "recent_created", "label": "Created in Last 7 Days"},
                {"key": "custom_date", "label": "Custom Date Range"},
            ],
            "metric": [
                {"key": "followers", "label": "Most Followers"},
                {"key": "friends", "label": "Most Friends"},
                {"key": "posts", "label": "Most Posts"},
                {"key": "views", "label": "Most Viewed"},
                {"key": "likes", "label": "Most Liked"},
                {"key": "comments", "label": "Most Commented"},
                {"key": "shares", "label": "Most Shared"},
                {"key": "recent_created", "label": "Recently Created"},
            ],
            "order": [
                {"key": "asc", "label": "Ascending"},
                {"key": "desc", "label": "Descending"},
            ],
            "date_filter": [
                {"key": "today", "label": "Today"},
                {"key": "7d", "label": "Last 7 Days"},
                {"key": "30d", "label": "Last 30 Days"},
                {"key": "custom", "label": "Custom Date Range"},
            ],
            "fields_in_response": [
                "id",
                "username",
                "city__name",
                "state__name",
                "country__name",
                "created_at",
                'profile_picture',
                "last_active_at",
                "metric_val"
            ]
        }
        return Response(options)

   
            
class ProfileAnalyticsView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            qs = Profile.objects.all()
            end_dt = now()

            # --- query params ---
            profile_scope = request.query_params.get("profile_scope", "all")
            metric        = request.query_params.get("metric", "followers")
            order         = request.query_params.get("order", "desc")
            date_filter   = request.query_params.get("date_filter")  # today|7d|30d|custom
            start_param   = request.query_params.get("start_date")
            end_param     = request.query_params.get("end_date")

            # --- scope filters on profiles ---
            if profile_scope == "verified":
                qs = qs.filter(is_verified=True)
            elif profile_scope == "active":
                start_of_week = end_dt - timedelta(days=end_dt.weekday())
                qs = qs.filter(last_active_at__gte=start_of_week)
            elif profile_scope == "recent_created":
                qs = qs.filter(created_at__gte=end_dt - timedelta(days=7))
            elif profile_scope == "custom_date" and start_param and end_param:
                qs = qs.filter(created_at__range=[start_param, end_param])

            # --- compute date window (for post-based metrics) ---
            win_start = win_end = None
            if date_filter == "today":
                win_start = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                win_end   = end_dt
            elif date_filter == "7d":
                win_start = end_dt - timedelta(days=7)
                win_end   = end_dt
            elif date_filter == "30d":
                win_start = end_dt - timedelta(days=30)
                win_end   = end_dt
            elif date_filter == "custom" and start_param and end_param:
                # accept YYYY-MM-DD or full ISO datetimes
                sd = parse_datetime(start_param) or (
                    parse_date(start_param) and datetime.datetime.combine(parse_date(start_param), datetime.time.min)
                )
                ed = parse_datetime(end_param) or (
                    parse_date(end_param) and datetime.datetime.combine(parse_date(end_param), datetime.time.max)
                )
                win_start, win_end = sd, ed

            # filtered Q for posts window (only if window present)
            post_window_q = Q()
            if win_start and win_end:
                post_window_q = Q(posts__created_at__gte=win_start, posts__created_at__lte=win_end)

            # --- metrics ---
            metric_map = {
                # M2M follower/friend counts (global — no timestamps on the relation to filter by)
                "followers": Count("followers", distinct=True),
                "friends":   Count("friends",   distinct=True),

                # post-based metrics (respect date window if provided)
                "posts":    Count("posts",              filter=post_window_q, distinct=True),
                "likes":    Coalesce(Sum("posts__reaction_count", filter=post_window_q), 0),
                "comments": Coalesce(Sum("posts__comment_count",  filter=post_window_q), 0),
                "shares":   Coalesce(Sum("posts__share_count",    filter=post_window_q), 0),

                # profile fields
                "views":           F("view_count"),
                "recent_created":  F("created_at"),
            }

            if metric not in metric_map:
                return Response(error_response(f"Invalid metric '{metric}'"), status=status.HTTP_400_BAD_REQUEST)

            qs = qs.annotate(metric_val=metric_map[metric])

            # --- ordering ---
            qs = qs.order_by("-metric_val" if order == "desc" else "metric_val")
            qs = qs.values(
                    "id",
                    "username",
                    "city__name",
                    "state__name",
                    "country__name",
                    "created_at",
                    'profile_picture',
                    "last_active_at",
                    "metric_val",
                )

            # --- pagination ---
            page = self.paginate_queryset(qs, request)
            data = list(page)

            return self.get_paginated_response(success_response(data))

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostFilterOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "post_scope": [
                {"key": "all", "label": "All Posts"},
                {"key": "published", "label": "Published Posts"},
                {"key": "drafts", "label": "Drafts"},
                {"key": "pinned", "label": "Pinned Posts"},
                {"key": "featured", "label": "Featured Posts"},
                {"key": "custom_date", "label": "Custom Date Range"},
            ],
            "metric": [
                {"key": "views", "label": "Most Viewed"},
                {"key": "likes", "label": "Most Liked"},
                {"key": "comments", "label": "Most Commented"},
                {"key": "shares", "label": "Most Shared"},
                {"key": "recent_created", "label": "Recently Created"},
                {"key": "saved", "label": "Most Saved"},
                {"key": "mentions", "label": "Most Mentioned"},
            ],
            "order": [
                {"key": "asc", "label": "Ascending"},
                {"key": "desc", "label": "Descending"},
            ],
            "date_filter": [
                {"key": "today", "label": "Today"},
                {"key": "7d", "label": "Last 7 Days"},
                {"key": "30d", "label": "Last 30 Days"},
                {"key": "custom", "label": "Custom Date Range"},
            ],
            "fields_in_response": [
                "id",
                "title",
                "profile__username",
                "city__name",
                "state__name",
                "country__name",
                "created_at",
                "updated_at",
                "metric_val"
            ]
        }
        return Response(data)


from post.models import Post, PostStatus, PostVisibility

class PostAnalyticsView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # --- Params ---
            post_scope = request.query_params.get("post", "all")
            metric = request.query_params.get("metric", "views")
            order = request.query_params.get("order", "desc")
            date_filter = request.query_params.get("date_filter")
            start_date = request.query_params.get("start_date")
            end_date_param = request.query_params.get("end_date")
            limit = int(request.query_params.get("limit", 10))

            qs = Post.objects.all()

            # --- Scope filters ---
            if post_scope == "published":
                qs = qs.filter(status=PostStatus.PUBLISHED)
            elif post_scope == "drafts":
                qs = qs.filter(status=PostStatus.DRAFT)
            elif post_scope == "pinned":
                qs = qs.filter(is_pinned=True)
            elif post_scope == "featured":
                qs = qs.filter(is_featured=True)

            # --- Date filters ---
            end_date = timezone.now()
            if date_filter == "today":
                qs = qs.filter(created_at__date=end_date.date())
            elif date_filter == "7d":
                qs = qs.filter(created_at__gte=end_date - timedelta(days=7))
            elif date_filter == "30d":
                qs = qs.filter(created_at__gte=end_date - timedelta(days=30))
            elif date_filter == "custom" and start_date and end_date_param:
                qs = qs.filter(created_at__range=[start_date, end_date_param])

            # --- Metric annotation ---
            metric_map = {
                "views": F("view_count"),
                "likes": F("reaction_count"),
                "comments": F("comment_count"),
                "shares": F("share_count"),
                "saved": Count("saved_by"),
                "mentions": Count("mentions"),
                "recent_created": F("created_at"),
            }

            if metric not in metric_map:
                return Response(error_response("Invalid metric"), status=400)

            qs = qs.annotate(metric_val=metric_map[metric])

            # --- Order ---
            order_field = "metric_val" if order == "desc" else "metric_val"
            qs = qs.order_by(f"-{order_field}" if order == "desc" else order_field)

            # --- Response fields ---
            qs = qs.values(
                "id",
                "title",
                "profile__username",
                "city__name",
                "state__name",
                "country__name",
                "created_at",
                "updated_at",
                "metric_val",
            )

            # --- Pagination ---
            page = self.paginate_queryset(qs, request)
            data = list(page)

            return self.get_paginated_response(success_response(data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)


class EventFilterOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "event_scope": [
                {"key": "all", "label": "All Events"},
                {"key": "upcoming", "label": "Upcoming Events"},
                {"key": "past", "label": "Past Events"},
                {"key": "published", "label": "Published Events"},
                {"key": "draft", "label": "Draft Events"},
                {"key": "custom_date", "label": "Custom Date Range"},
            ],
            "metric": [
                {"key": "views", "label": "Most Viewed"},
                {"key": "comments", "label": "Most Commented"},
                {"key": "shares", "label": "Most Shared"},
                {"key": "attendees", "label": "Most Attended"},
                {"key": "interested", "label": "Most Interested"},
                {"key": "not_interested", "label": "Most Not Interested"},
                {"key": "pending", "label": "Most Pending"},
                {"key": "recent_created", "label": "Recently Created"},
            ],
            "order": [
                {"key": "asc", "label": "Ascending"},
                {"key": "desc", "label": "Descending"},
            ],
            "date_filter": [
                {"key": "today", "label": "Today"},
                {"key": "7d", "label": "Last 7 Days"},
                {"key": "30d", "label": "Last 30 Days"},
                {"key": "custom", "label": "Custom Date Range"},
            ],
            "fields_in_response": [
                "id",
                "title",
                "host__username",
                "city__name",
                "state__name",
                "country__name",
                "start_datetime",
                "end_datetime",
                "created_at",
                "metric_val",
            ]
        }
        return Response(data)


class EventAnalyticsView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # --- Params ---
            event_scope = request.query_params.get("event_scope", "all")
            metric = request.query_params.get("metric", "views")
            order = request.query_params.get("order", "desc")
            date_filter = request.query_params.get("date_filter")
            start_date = request.query_params.get("start_date")
            end_date_param = request.query_params.get("end_date")
            limit = int(request.query_params.get("limit", 10))

            qs = Event.objects.all()
            now = timezone.now()

            # --- Scope filters ---
            if event_scope == "upcoming":
                qs = qs.filter(start_datetime__gte=now)
            elif event_scope == "past":
                qs = qs.filter(end_datetime__lt=now)
            elif event_scope == "published":
                qs = qs.filter(status=EventStatus.PUBLISHED)
            elif event_scope == "draft":
                qs = qs.filter(status=EventStatus.DRAFT)

            # --- Date filters ---
            end_date = timezone.now()
            if date_filter == "today":
                qs = qs.filter(created_at__date=end_date.date())
            elif date_filter == "7d":
                qs = qs.filter(created_at__gte=end_date - timedelta(days=7))
            elif date_filter == "30d":
                qs = qs.filter(created_at__gte=end_date - timedelta(days=30))
            elif date_filter == "custom" and start_date and end_date_param:
                qs = qs.filter(created_at__range=[start_date, end_date_param])

            # --- Metric annotation ---
            metric_map = {
                "views": F("view_count"),
                "comments": F("comment_count"),
                "shares": F("share_count"),
                "attendees": Count("attendees", distinct=True),
                "interested": Count("eventattendance", filter=Q(eventattendance__status=AttendanceStatus.INTERESTED)),
                "not_interested": Count("eventattendance", filter=Q(eventattendance__status=AttendanceStatus.NOT_INTERESTED)),
                "pending": Count("eventattendance", filter=Q(eventattendance__status=AttendanceStatus.PENDING)),
                "recent_created": F("created_at"),
            }

            if metric not in metric_map:
                return Response(error_response("Invalid metric"), status=400)

            qs = qs.annotate(metric_val=metric_map[metric])

            # --- Ordering ---
            order_field = "metric_val"
            qs = qs.order_by(f"-{order_field}" if order == "desc" else order_field)

            # --- Values for response ---
            qs = qs.values(
                "id",
                "title",
                "host__username",
                "city__name",
                "state__name",
                "country__name",
                "start_datetime",
                "end_datetime",
                "created_at",
                "metric_val",
            )[:limit]

            # --- Pagination ---
            page = self.paginate_queryset(qs, request)
            data = list(page)

            return self.get_paginated_response(success_response(data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)
        

class GroupFilterOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            "group_scope": [
                {"key": "all", "label": "All Groups"},
                {"key": "public", "label": "Public Groups"},
                {"key": "private", "label": "Private Groups"},
                {"key": "featured", "label": "Featured Groups"},
                {"key": "recent_created", "label": "Recently Created"},
                {"key": "custom_date", "label": "Custom Date Range"},
            ],
            "metric": [
                {"key": "members", "label": "Most Members"},
                {"key": "posts", "label": "Most Posts"},
                {"key": "avg_engagement", "label": "Highest Avg Engagement"},
                {"key": "trending_score", "label": "Trending Score"},
                {"key": "last_activity", "label": "Most Recently Active"},
                {"key": "recent_created", "label": "Recently Created"},
            ],
            "order": [
                {"key": "asc", "label": "Ascending"},
                {"key": "desc", "label": "Descending"},
            ],
            "date_filter": [
                {"key": "today", "label": "Today"},
                {"key": "7d", "label": "Last 7 Days"},
                {"key": "30d", "label": "Last 30 Days"},
                {"key": "custom", "label": "Custom Date Range"},
            ],
            "fields_in_response": [
                "id",
                "name",
                "slug",
                "type",
                "privacy",
                "member_count",
                "post_count",
                "avg_engagement",
                "trending_score",
                "last_activity_at",
                "created_at",
                "metric_val"
            ]
        }
        return Response(data)


class GroupAnalyticsView(APIView, PaginationMixin):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # --- Params ---
            group_scope = request.query_params.get("group_scope", "all")  # ✅ consistent with filter options
            metric = request.query_params.get("metric", "members")
            order = request.query_params.get("order", "desc")
            date_filter = request.query_params.get("date_filter")
            start_date = request.query_params.get("start_date")
            end_date_param = request.query_params.get("end_date")
            limit = int(request.query_params.get("limit", 10))

            qs = Group.objects.all()
            now = timezone.now()

            # --- Scope filters ---
            if group_scope == "public":
                qs = qs.filter(privacy="PUBLIC")
            elif group_scope == "private":
                qs = qs.filter(privacy="PRIVATE")
            elif group_scope == "featured":
                qs = qs.filter(featured=True)
            elif group_scope == "recent_created":
                qs = qs.filter(created_at__gte=now - timedelta(days=7))
            elif group_scope == "custom_date" and start_date and end_date_param:
                qs = qs.filter(created_at__range=[start_date, end_date_param])

            # --- Date filters ---
            if date_filter == "today":
                qs = qs.filter(created_at__date=now.date())
            elif date_filter == "7d":
                qs = qs.filter(created_at__gte=now - timedelta(days=7))
            elif date_filter == "30d":
                qs = qs.filter(created_at__gte=now - timedelta(days=30))
            elif date_filter == "custom" and start_date and end_date_param:
                qs = qs.filter(created_at__range=[start_date, end_date_param])

            # --- Metric mapping ---
            metric_map = {
                "members": F("member_count"),
                "posts": F("post_count"),
                "avg_engagement": F("avg_engagement"),
                "trending_score": F("trending_score"),
                "last_activity": F("last_activity_at"),
                "recent_created": F("created_at"),
            }

            if metric not in metric_map:
                return Response(error_response("Invalid metric"), status=400)

            qs = qs.annotate(metric_val=metric_map[metric])

            # --- Ordering ---
            order_field = "metric_val"
            qs = qs.order_by(f"-{order_field}" if order == "desc" else order_field)

            # --- Values ---
            qs = qs.values(
                "id",
                "name",
                "slug",
                "type",
                "privacy",
                "member_count",
                "post_count",
                "avg_engagement",
                "trending_score",
                "last_activity_at",
                "created_at",
                "metric_val"
            )

            # --- Pagination ---
            page = self.paginate_queryset(qs, request)
            data = list(page)

            return self.get_paginated_response(success_response(data))

        except Exception as e:
            return Response(error_response(str(e)), status=500)
