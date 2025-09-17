from django.urls import path
from chat.consumers import ChatConsumer, ActiveChatsConsumer, PresenceConsumer

websocket_urlpatterns = [
    path('ws/chat/<str:group_id>/', ChatConsumer.as_asgi()),
    path('ws/active-chats/', ActiveChatsConsumer.as_asgi()),
    path('ws/user-presence/', PresenceConsumer.as_asgi()),
    
]