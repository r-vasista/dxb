# Rest Framework imports
from rest_framework import serializers

# Local imports
from post.models import (
    Post, PostMedia, PostReaction, Comment, CommentLike, Hashtag, SharePost, ArtType, CustomArtType
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
    art_type_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    custom_art_type_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    # Read-only serialized fields
    art_types = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )
    custom_art_types = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )


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
    
    def create(self, validated_data):
        art_type_ids = validated_data.pop('art_type_ids', [])
        custom_names = validated_data.pop('custom_art_type_names', [])
        print('custom names', custom_names)
        post = Post.objects.create(**validated_data)
        self._assign_art_types(post, art_type_ids, custom_names)
        return post

    def update(self, instance, validated_data):
        art_type_ids = validated_data.pop('art_type_ids', [])
        custom_names = validated_data.pop('custom_art_type_names', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.art_types.clear()
        instance.custom_art_types.clear()
        self._assign_art_types(instance, art_type_ids, custom_names)
        return instance

    def _assign_art_types(self, post, art_type_ids, custom_names):
        # Assign existing ArtTypes by ID
        art_types = ArtType.objects.filter(id__in=art_type_ids)
        post.art_types.set(art_types)

        # Create or get CustomArtTypes (normalized in model save)
        for name in custom_names:
            obj, _ = CustomArtType.objects.get_or_create(name=name)
            post.custom_art_types.add(obj)


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


class HashtagSerializer(serializers.ModelSerializer):
    """
    Serializer for Hash Tags
    """
    
    class Meta:
        model = Hashtag
        fields = ['name']


class SharePostSerailizer(serializers.ModelSerializer):
    class Meta:
        model = SharePost 
        fields = '__all__'


class ArtTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtType
        fields = ['id', 'name', 'slug', 'description']
