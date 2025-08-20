# Django imports
from django.db.models import Q
from django.utils import timezone

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

