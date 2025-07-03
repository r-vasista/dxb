# Django imports

# Rest Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError


# Local imports
from core.models import Country, State, City
from core.serializers import CountrySerializer, StateSerializer, CitySerializer
from core.services import success_response, error_response

class LocationHierarchyAPIView(APIView):
    """
    GET /api/locations/?country_id=<id>&state_id=<id>

    Handles:
    - No params → return all countries
    - country_id only:
        → if states exist → return states
        → if no states exist → return cities directly
    - state_id → return cities in that state
    """
    def get(self, request):
        try:
            country_id = request.query_params.get('country_id')
            state_id = request.query_params.get('state_id')

            if state_id:
                cities = City.objects.filter(state_id=state_id)
                serializer = CitySerializer(cities, many=True)
                return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

            elif country_id:
                states = State.objects.filter(country_id=country_id)
                if states.exists():
                    serializer = StateSerializer(states, many=True)
                    return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)
                else:
                    # Fallback: if no states, return cities directly
                    cities = City.objects.filter(country_id=country_id, state__isnull=True)
                    serializer = CitySerializer(cities, many=True)
                    return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

            else:
                countries = Country.objects.all()
                serializer = CountrySerializer(countries, many=True)
                return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(error_response(e.detail), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
