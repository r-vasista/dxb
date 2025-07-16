from django.urls import path
from event.views import (
    CreateEventAPIView, EventListAPIView, EventAttendacneAPIView, MyRSVPEventsListAPIView, EventMediaUploadAPIView, EventMediaListAPIView,
    UpdateEventAPIView
)


urlpatterns = [
    path('create/', CreateEventAPIView.as_view(), name='create'),
    path('update/<int:event_id>/', UpdateEventAPIView.as_view(), name='update'),
    path('list/', EventListAPIView.as_view(), name='event-list'),
    path('rsvp/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('rsvp/<int:event_id>/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('rsvp/<int:event_id>/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('my-rsvp-events/', MyRSVPEventsListAPIView.as_view(), name='my-rsvp-events'),
    path('upload-media/<int:event_id>/', EventMediaUploadAPIView.as_view(), name='upload-media'),
    path('media-list/<int:event_id>/', EventMediaListAPIView.as_view(), name='media-list'),
]
