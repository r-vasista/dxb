# Django imports
from django.db import models
from django.db.models import Prefetch

# Rest Framework imports
from rest_framework import serializers

# Local imports
from profiles.models import (
    ProfileField, Profile, FriendRequest, ProfileFieldSection, ProfileCanvas, StaticProfileField, StaticFieldValue, StaticProfileSection
)
from profiles.utils import (
    validate_profile_field_data
)
from organization.serializers import (
    OrganizationSerializer
)
from core.services import get_user_profile


class StaticFieldValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticFieldValue
        fields = ['field_value']


class StaticProfileFieldSerializer(serializers.ModelSerializer):
    field_value = serializers.SerializerMethodField()

    class Meta:
        model = StaticProfileField
        fields = ['id', 'field_name', 'description', 'is_public', 'display_order', 'field_value']

    def get_field_value(self, field):
        profile = self.context.get('profile')
        if not profile:
            return None
        response = StaticFieldValue.objects.filter(profile=profile, static_field=field).first()
        return StaticFieldValueSerializer(response).data['field_value'] if response else None
    

class StaticProfileSectionSerializer(serializers.ModelSerializer):
    static_fields = serializers.SerializerMethodField()

    class Meta:
        model = StaticProfileSection
        fields = ['id', 'title', 'description', 'display_order', 'static_fields']

    def get_static_fields(self, obj):
        fields = obj.fields.all().order_by('display_order')
        return StaticProfileFieldSerializer(fields, many=True, context=self.context).data

class ProfileSerializer(serializers.ModelSerializer):
    profile_fields = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    friends_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'bio', 'profile_picture', 'profile_type', 'cover_picture', 'visibility_status',
            'followers_count', 'friends_count', 'following_count',
            'organization', 'profile_fields'
        ]

    def get_profile_fields(self, obj):
        from profiles.models import ProfileField  # Prevent circular import
        fields = ProfileField.objects.filter(profile=obj)
        return ProfileFieldSerializer(fields, many=True).data

    def get_organization(self, obj):
        if obj.organization:
            return OrganizationSerializer(obj.organization).data
        return None

    

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['username', 'bio', 'profile_picture', 'cover_picture', 'visibility_status', 'city', 'country', 'state']
        extra_kwargs = {
            'username': {'required': False}, 
        }


class ProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_public']
        extra_kwargs = {'field_type': {'required': True}}

    def get_value(self, obj):
        return obj.get_value()

    def validate(self, data):
        validate_profile_field_data(data)
        return data


class UpdateProfileFieldSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = ProfileField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'profile']
        extra_kwargs = {'field_type': {'required': True}}

    def get_value(self, obj):
        return obj.get_value()

    def validate(self, data):
        instance = getattr(self, 'instance', None)
        if instance:
            data = {**self.initial_data, **data}
        validate_profile_field_data(data, instance=instance)
        return data
    

class ProfileFieldSectionSerializer(serializers.ModelSerializer):
    fields = ProfileFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProfileFieldSection
        fields = ['id', 'title', 'description', 'display_order', 'fields']

class ProfileDetailSerializer(serializers.ModelSerializer):
    field_sections = ProfileFieldSectionSerializer(many=True, read_only=True)
    static_sections = serializers.SerializerMethodField()

    is_friend = serializers.SerializerMethodField()
    friend_request_status = serializers.SerializerMethodField()
    got_friend_request = serializers.SerializerMethodField()
    
    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'bio', 'profile_picture', 'cover_picture',
            'profile_type', 'visibility_status',
            'followers_count', 'following_count', 'friends_count',
            'field_sections', 'is_friend', 'friend_request_status', 'static_sections',
            'got_friend_request'
        ]
    
    def get_is_friend(self, obj):
        """
        Check if the request user's profile is friends with the target profile.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        try:
            user_profile = get_user_profile(request.user)
            return obj in user_profile.friends.all()
        except Profile.DoesNotExist:
            return False
        
    def get_friend_request_status(self, obj):
        """
        Determine the current friend request status between the logged-in user's profile and the target profile.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            user_profile = get_user_profile(request.user)

            if user_profile == obj:
                return None  # You can't send a request to yourself

            # Try to find a friend request either direction
            friend_request = FriendRequest.objects.filter(
                from_profile=user_profile, to_profile=obj
            ).order_by('-created_at').first()

            return friend_request.status if friend_request else None

        except Profile.DoesNotExist:
            return None
    
    def get_got_friend_request(self, obj):
        """
        Determine the current friend request status between the logged-in user's profile and the target profile.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            user_profile = get_user_profile(request.user)

            if user_profile == obj:
                return None  # You can't send a request to yourself

            # Try to find a friend request either direction
            friend_request = FriendRequest.objects.filter(
                from_profile=obj, to_profile=user_profile, status='pending'
            ).first()

            return friend_request.id if friend_request else False

        except Profile.DoesNotExist:
            return False
    
    def get_static_sections(self, obj):
        sections = StaticProfileSection.objects.prefetch_related(
            Prefetch(
                'fields',
                queryset=StaticProfileField.objects.all().order_by('display_order')
            )
        ).order_by('display_order')
        
        serializer = StaticProfileSectionSerializer(sections, many=True, context={'profile': obj})
        return serializer.data


class FriendRequestSerializer(serializers.ModelSerializer):
    from_profile_id = serializers.IntegerField(source='from_profile.id', read_only=True)
    from_username = serializers.CharField(source='from_profile.username', read_only=True)
    from_profile_pic = serializers.ImageField(source='from_profile.profile_picture', read_only=True)

    class Meta:
        model = FriendRequest
        fields = [
            'id',
            'from_profile_id',
            'from_username',
            'from_profile_pic',
            'status',
        ]


class UpdateProfileFieldSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileFieldSection
        fields = ['title', 'description', 'display_order']
    

class ProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'username', 'profile_picture', 'bio']


class ProfileCanvasSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileCanvas
        fields = ['id', 'profile', 'image', 'display_order', 'created_by']
        read_only_fields = ['id', 'profile', 'created_by']
    
    def create(self, validated_data):
        profile = validated_data['profile']

        # Get the highest existing display_order for this profile
        last_order = ProfileCanvas.objects.filter(profile=profile).aggregate(
            max_order=models.Max('display_order')
        )['max_order'] or 0

        # Set the next display_order
        validated_data['display_order'] = last_order + 1

        return super().create(validated_data)


class StaticFieldInputSerializer(serializers.Serializer):
    static_field_id = serializers.IntegerField()
    field_value = serializers.CharField(allow_blank=True, required=False)

    def validate_static_field_id(self, value):
        if not StaticProfileField.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid static_field_id.")
        return value