from django.urls import path
from core.views import (
    LocationHierarchyAPIView, CountrySearchView, StateSearchView, CitySearchView, UpcomingFeatureAPIView, WeeklyChallengeAPIView,
)

urlpatterns = [
     path('locations/', LocationHierarchyAPIView.as_view(), name='location-hierarchy'),
     path('search/countries/', CountrySearchView.as_view(), name='search-countries'),
     path('search/states/', StateSearchView.as_view(), name='search-states'),
     path('search/cities/', CitySearchView.as_view(), name='search-cities'),
     path('weekly-challenge/', WeeklyChallengeAPIView.as_view(), name='weekly-challenge'),

     path('upcoming-features/', UpcomingFeatureAPIView.as_view(), name='upcoming-features'),
]
