from django.urls import path
from core.views import LocationHierarchyAPIView, CountrySearchView, StateSearchView, CitySearchView

urlpatterns = [
     path('locations/', LocationHierarchyAPIView.as_view(), name='location-hierarchy'),
     path('search/countries/', CountrySearchView.as_view(), name='search-countries'),
     path('search/states/', StateSearchView.as_view(), name='search-states'),
     path('search/cities/', CitySearchView.as_view(), name='search-cities'),
]
