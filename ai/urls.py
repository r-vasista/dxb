# urls.py
from django.urls import path
from .views import ArtImageDescribeAPIView, EventTagAIAPIView

urlpatterns = [
    path('art/describe/', ArtImageDescribeAPIView.as_view(), name='art-image-describe'),
    path('event/tags/', EventTagAIAPIView.as_view(), name='event-tags'),
]
