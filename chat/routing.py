from django.urls import path
from chat.consumers import ChatConsumer, ActiveChatsConsumer

websocket_urlpatterns = [
    path('ws/chat/<str:group_id>/', ChatConsumer.as_asgi()),
    path('ws/active-chats/', ActiveChatsConsumer.as_asgi()),
    
]