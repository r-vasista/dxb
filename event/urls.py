from django.urls import path
from event.views import (
    CreateEventAPIView, EventListAPIView, EventAttendacneAPIView, MyRSVPEventsListAPIView, EventMediaUploadAPIView, EventMediaListAPIView,
    UpdateEventAPIView, EventCommentCreateAPIView, ParentEventCommentListAPIView, ChildEventCommentListAPIView, EventMediaPinStatusAPIView,
    PopularEventsAPIView, CreateEventMediaCommentAPIView, ParentEventMediaCommentsAPIView, ChildEventMediaCommentListAPIView, 
    EventDetailAPIView
)


urlpatterns = [
    path('create/', CreateEventAPIView.as_view(), name='create'),
    path('details/<int:event_id>/', EventDetailAPIView.as_view(), name='detials'),
    path('update/<int:event_id>/', UpdateEventAPIView.as_view(), name='update'),
    path('list/', EventListAPIView.as_view(), name='event-list'),
    path('rsvp/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('rsvp/<int:event_id>/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('rsvp/<int:event_id>/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('my-rsvp-events/', MyRSVPEventsListAPIView.as_view(), name='my-rsvp-events'),
    path('upload-media/<int:event_id>/', EventMediaUploadAPIView.as_view(), name='upload-media'),
    path('media-list/<int:event_id>/', EventMediaListAPIView.as_view(), name='media-list'),
    path('comment/<int:event_id>/', EventCommentCreateAPIView.as_view(), name='event-comment'),
    path('parent-comments-list/<int:event_id>/', ParentEventCommentListAPIView.as_view(), name='parent-event-comments'),
    path('child-comments-list/<int:event_id>/<int:parent_id>/', ChildEventCommentListAPIView.as_view(), name='child-event-comments'),
    path('pin-media/<int:event_id>/<int:media_id>/', EventMediaPinStatusAPIView.as_view(), name='pin-event-media'),
    path('popular-events/', PopularEventsAPIView.as_view(), name='popular-events'),
    path('comment-media/<str:event_media_id>/', CreateEventMediaCommentAPIView.as_view(), name='comment-media'),
    path('parent-media-comments-list/<int:evnet_media_id>/', ParentEventMediaCommentsAPIView.as_view(), name='parent-event-media-comments'),
    path('child-media-comments-list/<int:event_media_id>/<int:parent_id>/', ChildEventMediaCommentListAPIView.as_view(), name='child-event-media-comments'),

]
