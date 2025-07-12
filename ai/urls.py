# urls.py
from django.urls import path
from .views import ArtImageDescribeAPIView

urlpatterns = [
    path('art/describe/', ArtImageDescribeAPIView.as_view(), name='art-image-describe'),
]
