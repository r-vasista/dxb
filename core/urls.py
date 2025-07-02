from django.urls import path
from core.views import LocationHierarchyAPIView

urlpatterns = [
     path('locations/', LocationHierarchyAPIView.as_view(), name='location-hierarchy'),
]
