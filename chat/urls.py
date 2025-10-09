from django.urls import path
from .views import (
    EnsurePersonalChatAPIView, MyChatGroupsAPIView, GroupMessagesAPIView, SendMessageAPIView,
    MarkAllMessagesReadAPIView, MarkMessagesReadByIdAPIView, MyActiveChatsAPIView, DeleteMessageAPIView, ScheduleMessageAPIView,
    UploadAndApplyChatThemeAPIView, RemoveChatThemeAPIView
)

urlpatterns = [
    path("personal-chat/<int:profile_id>/", EnsurePersonalChatAPIView.as_view()),
    path("my-groups/", MyChatGroupsAPIView.as_view()),
    path("groups/messages/<str:group_id>/", GroupMessagesAPIView.as_view()),
    path("message/send/<uuid:group_id>/", SendMessageAPIView.as_view()),
    path("mark-read/all/<uuid:group_id>/", MarkAllMessagesReadAPIView.as_view(), name="mark_all_read"),
    path("mark-read/<uuid:group_id>/", MarkMessagesReadByIdAPIView.as_view(), name="mark_read_by_ids"),
    path("my-active-chats/", MyActiveChatsAPIView.as_view(), name="my-active-chats"),
    path("delete-message/<int:message_id>/", DeleteMessageAPIView.as_view(), name="delete-message"),
    path("schedule-message/<str:group_id>/", ScheduleMessageAPIView.as_view(), name="schedule-message"),
    path("apply-chat-theme/", UploadAndApplyChatThemeAPIView.as_view(), name="apply-chat-theme"),
    path("remove-chat-theme/", RemoveChatThemeAPIView.as_view(), name="remove-chat-theme"),
    
]
