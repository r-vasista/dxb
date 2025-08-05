from django.urls import path

from group.views import GroupCreateAPIView

urlpatterns = [
    path('create-group/', GroupCreateAPIView.as_view(), name='create-group')
]
