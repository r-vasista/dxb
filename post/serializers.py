# Rest Framework imports
from rest_framework import serializers

# Local imports
from post.models import (
    Post, PostMedia
)

class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'media_type', 'order']


class PostSerializer(serializers.ModelSerializer):
    media = PostMediaSerializer(many=True, read_only=True)
    username = serializers.CharField(source='profile.username', read_only=True)

    class Meta:
        model = Post
        fields = '__all__'
