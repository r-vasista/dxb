from django.urls import path
from event.views import (
    CreateEventAPIView, EventListAPIView, EventAttendacneAPIView, MyRSVPEventsListAPIView, EventMediaUploadAPIView, EventMediaListAPIView,
    UpdateEventAPIView, EventCommentCreateAPIView, ParentEventCommentListAPIView, ChildEventCommentListAPIView, EventMediaPinStatusAPIView,
    PopularEventsAPIView, CreateEventMediaCommentAPIView, ParentEventMediaCommentsAPIView, ChildEventMediaCommentListAPIView, 
    EventDetailAPIView,SuggestedEventsAPIView,EventMediaDetailAPIView, MyHostedEventsAPIView, AddCoHostsAPIView, RemoveCoHostAPIView,
    ApproveRSVPAPIView, EventMediaLikeAPIView, EventMediaLikeDetailAPIView, EventMediaLikesByIdAPIView, EventListByHostOrCoHostAPIView, 
    EventMediaCommentLikeToggleAPIView, EventMediaCommentLikeListAPIView, GetCoHostListAPIView, EventViewActivityAPIView, EventShareActivityAPIView, EventAnalyticsAPIView, 
    ShareEventWithProfilesAPIView, PublicEventDetailAPIView, DownloadEventAttendanceExcel
)


urlpatterns = [
    path('create/', CreateEventAPIView.as_view(), name='create'),
    path('details/<int:event_id>/', EventDetailAPIView.as_view(), name='detials'),
    path('details/<str:slug>/', EventDetailAPIView.as_view(), name='detials'),
    path('public-details/<int:event_id>/', PublicEventDetailAPIView.as_view(), name='detials'),
    path('public-details/<str:slug>/', PublicEventDetailAPIView.as_view(), name='detials'),
    path('update/<int:event_id>/', UpdateEventAPIView.as_view(), name='update'),
    path('list/', EventListAPIView.as_view(), name='event-list'),
    path('rsvp/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('rsvp/<int:event_id>/', EventAttendacneAPIView.as_view(), name='event-rsvp'),
    path('my-rsvp-events/', MyRSVPEventsListAPIView.as_view(), name='my-rsvp-events'),
    path('upload-media/<int:event_id>/', EventMediaUploadAPIView.as_view(), name='upload-media'),
    path('media-list/<int:event_id>/', EventMediaListAPIView.as_view(), name='media-list'),
    path('media/<int:media_id>/', EventMediaDetailAPIView.as_view(), name='event-media-detail'),
    path('comment/<int:event_id>/', EventCommentCreateAPIView.as_view(), name='event-comment'),
    path('parent-comments-list/<int:event_id>/', ParentEventCommentListAPIView.as_view(), name='parent-event-comments'),
    path('child-comments-list/<int:event_id>/<int:parent_id>/', ChildEventCommentListAPIView.as_view(), name='child-event-comments'),
    path('pin-media/<int:event_id>/<int:media_id>/', EventMediaPinStatusAPIView.as_view(), name='pin-event-media'),
    path('popular-events/', PopularEventsAPIView.as_view(), name='popular-events'),
    path('comment-media/<str:event_media_id>/', CreateEventMediaCommentAPIView.as_view(), name='comment-media'),
    path('parent-media-comments-list/<int:evnet_media_id>/', ParentEventMediaCommentsAPIView.as_view(), name='parent-event-media-comments'),
    path('child-media-comments-list/<int:event_media_id>/<int:parent_id>/', ChildEventMediaCommentListAPIView.as_view(), name='child-event-media-comments'),
    path('hosted-events/', MyHostedEventsAPIView.as_view(), name='hosted-events'),
    path('add-cohost/<int:event_id>/', AddCoHostsAPIView.as_view(), name='add-cohost'),
    path('remove-cohost/<int:event_id>/', RemoveCoHostAPIView.as_view(), name='remove-cohost'),
    path('suggest/event/',SuggestedEventsAPIView.as_view(),name='suggest-event-user'),
    path('event-media-likes/', EventMediaLikeAPIView.as_view(), name='event-media-like'),
    path('event-media-likes/<int:pk>/', EventMediaLikeDetailAPIView.as_view(), name='event-media-like-detail'),
    path('media/likes/<int:id>/', EventMediaLikesByIdAPIView.as_view(), name='event-media-likes-by-id'),
    path('events/owned/<str:username>/', EventListByHostOrCoHostAPIView.as_view(), name='event-owned-by-name'),
    path('approve-rsvp/', ApproveRSVPAPIView.as_view(), name='approve-rsvp'),

    path('eventmediacomment/like-toggle/', EventMediaCommentLikeToggleAPIView.as_view(), name='eventmedia-comment-like-toggle'),
    path('eventmediacomment/likes/<int:comment_id>/', EventMediaCommentLikeListAPIView.as_view(), name='eventmedia-comment-like-list'),
    
    path('co-hosts-list/<int:event_id>/', GetCoHostListAPIView.as_view(), name='co-hosts-list'),
    path('co-hosts-list/<str:event_slug>/', GetCoHostListAPIView.as_view(), name='co-hosts-list'),
    path('events/view/<int:event_id>/', EventViewActivityAPIView.as_view(), name='event-view-activity'),
    path('events/share_count/<int:event_id>/', EventShareActivityAPIView.as_view(), name='event-share-activity'),
    path('events/analytics/<int:event_id>/', EventAnalyticsAPIView.as_view(), name='event-analytics-activity'),
    path('share/event/bulk/', ShareEventWithProfilesAPIView.as_view(), name='share-event-bulk'),

    path('events/attendance/download/<int:event_id>/', DownloadEventAttendanceExcel.as_view(), name='download-attendance-excel'),

]
