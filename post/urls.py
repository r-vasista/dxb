from django.urls import path
from post.views import PostView

urlpatterns = [
    path('post/', PostView.as_view(), name='post')
]
