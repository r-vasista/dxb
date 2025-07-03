from django.urls import path
from event.views import CreateEventAPIView, EventListAPIView


urlpatterns = [
    path('create-event/', CreateEventAPIView.as_view(), name='create-event'),
    path('event-list/', EventListAPIView.as_view(), name='event-list'),
]
