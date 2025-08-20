from django.urls import path
from .views import (
    EnsurePersonalChatAPIView, MyChatGroupsAPIView, GroupMessagesAPIView, SendMessageAPIView,
    MarkAllMessagesReadAPIView, MarkMessagesReadByIdAPIView
)

urlpatterns = [
    path("personal-chat/<int:profile_id>/", EnsurePersonalChatAPIView.as_view()),
    path("my-groups/", MyChatGroupsAPIView.as_view()),
    path("groups/messages/<str:group_id>/", GroupMessagesAPIView.as_view()),
    path("groups/<uuid:group_id>/messages/send/", SendMessageAPIView.as_view()),
    path("mark-read/all/<uuid:group_id>/", MarkAllMessagesReadAPIView.as_view(), name="mark_all_read"),
    path("mark-read/<uuid:group_id>/", MarkMessagesReadByIdAPIView.as_view(), name="mark_read_by_ids"),
]
