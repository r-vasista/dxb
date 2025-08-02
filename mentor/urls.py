from django.urls import path
from .views import MentorProfileCreateView, MentorProfileDetailUpdateView

urlpatterns = [
    path('mentor-profile/create/', MentorProfileCreateView.as_view(), name='mentor-profile-create'),
    path('mentor-profile/', MentorProfileDetailUpdateView.as_view(), name='mentor-profile-detail'),
]
