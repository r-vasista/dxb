from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import ValidationError

from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer
from core.services import success_response, error_response  # assuming you have these helpers
from core.pagination import PaginationMixin


class SubscriptionListAPIView(APIView, PaginationMixin):
    """
    GET /api/subscriptions/

    Retrieves a paginated list of all available subscription plans.

    Example Response:
    {
        "status": true,
        "links": {
            "next": "http://127.0.0.1:8000/subscription/subscriptions-list/?page=2",
            "previous": null
        },
        "count": 12,
        "total_pages": 2,
        "current_page": 1,
        "data": [
            {
                "id": 1,
                "name": "Gold Plan",
                "description": "Access premium features",
                "price": "99.99",
                "currency": "USD",
                "duration_days": 30,
                "unlimited_edits": true,
                "canvas_frames": true,
                "custom_chat_themes": true,
                ...
            }
        ]
    }
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        try:
            queryset = SubscriptionPlan.objects.all().order_by("price")
            paginated_qs = self.paginate_queryset(queryset, request)

            serializer = SubscriptionPlanSerializer(paginated_qs, many=True)
            return self.get_paginated_response(serializer.data)

        except Http404:
            return error_response("No subscription plans found.", status.HTTP_404_NOT_FOUND)

        except ValidationError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return error_response(
                f"An unexpected error occurred while fetching subscriptions: {str(e)}",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
