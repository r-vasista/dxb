# Rest Framework imports
from rest_framework import serializers

# Local imports
from post.models import (
    Post, PostMedia, PostReaction, Comment, CommentLike, Hashtag
)
from core.serializers import TimezoneAwareSerializerMixin
from core.services import get_user_profile

class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'media_type', 'order']


class PostSerializer(TimezoneAwareSerializerMixin):
    media = PostMediaSerializer(many=True, read_only=True)
    username = serializers.CharField(source='profile.username', read_only=True)
    profile_picture = serializers.CharField(source='profile.profile_picture', read_only=True)
    hashtags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )
    user_reaction_type = serializers.SerializerMethodField()
    reaction_id=serializers.SerializerMethodField()
    allow_comments = serializers.BooleanField(default=True)
    allow_reactions = serializers.BooleanField(default=True)

    city_name = serializers.CharField(source='city.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)


    class Meta:
        model = Post
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'profile']
    
    def get_reaction_id(self,post):
        request=self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        profile = get_user_profile(request.user)
        if not profile:
            return None

        reaction=post.reactions.filter(profile=profile).first()
        return reaction.id if reaction else None

    def get_user_reaction_type(self, post):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        profile = get_user_profile(request.user)
        if not profile:
            return None

        # Check if the user reacted to this post
        reaction = post.reactions.filter(profile=profile).first()
        return reaction.reaction_type if reaction else None


class ImageMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'file', 'order']


class PostReactionSerializer(serializers.ModelSerializer):
    profile_username = serializers.CharField(source='profile.username', read_only=True)
    profile_picture = serializers.CharField(source='profile.profile_picture', read_only=True)

    class Meta:
        model = PostReaction
        fields = ['id', 'post', 'profile', 'profile_username','profile_picture', 'reaction_type', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    profile_username = serializers.CharField(source='profile.username', read_only=True)
    profile_picture = serializers.CharField(source='profile.profile_picture', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'profile', 'profile_username', 'profile_picture',
            'parent', 'content', 'like_count', 'reply_count',
            'is_approved', 'is_flagged', 'created_at', 'updated_at','replies'
        ]
        read_only_fields = ['created_at', 'updated_at', 'like_count', 'reply_count']
    def get_replies(self, obj):
        replies = obj.replies.filter(is_approved=True).order_by('created_at')
        return CommentSerializer(replies, many=True).data

class CommentLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentLike
        fields = ['id', 'comment', 'profile', 'created_at']
        read_only_fields = ['created_at']


class HashtagSerializer(serializers.ModelSerializer):
    """
    Serializer for Hash Tags
    """
    
    class Meta:
        model = Hashtag
        fields = ['name']
