from django.urls import path
from .views import (
    EnsurePersonalChatAPIView,
    MyChatGroupsAPIView,
    GroupMessagesAPIView,
    SendMessageAPIView,
    MarkReadAPIView,
)

urlpatterns = [
    path("personal-chat/<int:profile_id>/", EnsurePersonalChatAPIView.as_view()),
    path("my-groups/", MyChatGroupsAPIView.as_view()),
    path("groups/<uuid:group_id>/messages/", GroupMessagesAPIView.as_view()),
    path("groups/<uuid:group_id>/messages/send/", SendMessageAPIView.as_view()),
    path("groups/<uuid:group_id>/mark-read/", MarkReadAPIView.as_view()),
]
