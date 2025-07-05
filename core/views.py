# Django imports
from django.db.models import Q

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

# Local imports
from core.models import Country, State, City
from core.serializers import CountrySerializer, StateSerializer, CitySerializer
from core.services import success_response, error_response
from core.pagination import PaginationMixin


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
