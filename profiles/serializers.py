# Django imports
from django.db import models
from django.db.models import Prefetch

# Rest Framework imports
from rest_framework import serializers

# Python imports
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Local imports
from profiles.models import (
    ProfileField, Profile, FriendRequest, ProfileFieldSection, ProfileCanvas, StaticProfileField, StaticFieldValue, StaticProfileSection,
    ArtService, ArtServiceInquiry
)
from profiles.utils import (
    validate_profile_field_data
)
from profiles.choices import(
    StaticFieldType
)
from organization.serializers import (
    OrganizationSerializer
)
from core.services import get_user_profile
from event.serializers import (
    EventListSerializer
)


class StaticFieldValueSerializer(serializers.ModelSerializer):
    field_name = serializers.CharField(source='static_field.field_name', read_only=True)
    field_type = serializers.CharField(source='static_field.field_type', read_only=True)
    section_title = serializers.CharField(source='static_field.section.title', read_only=True)
    is_public = serializers.BooleanField(source='static_field.is_public', read_only=True)
    display_order = serializers.IntegerField(source='static_field.display_order', read_only=True)
    field_value = serializers.SerializerMethodField()

    class Meta:
        model = StaticFieldValue
        fields = ['id', 'field_name', 'field_type', 'section_title', 'is_public', 
                 'display_order', 'field_value', 'last_updated']

    def get_field_value(self, obj):
        """Return the appropriate value based on field type"""
        value = obj.get_value()
        
        if obj.static_field.field_type == StaticFieldType.DATE and value:
            return value.strftime('%Y-%m-%d')
        elif obj.static_field.field_type == StaticFieldType.IMAGE and value:
            if value:
                # Build absolute URL using request context
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(value.url)
                return value.url
            return None
        elif obj.static_field.field_type == StaticFieldType.FILE and value:
            if value:
                # Build absolute URL using request context
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(value.url)
                return value.url
            return None
        elif obj.static_field.field_type == StaticFieldType.NUMBER and value:
            return str(value)
        elif obj.static_field.field_type == StaticFieldType.BOOLEAN and value is not None:
            return value
        
        return value



class StaticProfileFieldSerializer(serializers.ModelSerializer):
    field_value = serializers.SerializerMethodField()

    class Meta:
        model = StaticProfileField
        fields = ['id', 'field_name', 'field_type', 'description', 'is_public', 'display_order', 'field_value']

    def get_field_value(self, field):
        profile = self.context.get('profile')
        if not profile:
            return None
        response = StaticFieldValue.objects.filter(profile=profile, static_field=field).first()
        return StaticFieldValueSerializer(response, context=self.context).data['field_value'] if response else None
    

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
            'organization', 'profile_fields', 'awards', 'tools'
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
        fields = [
            'username', 'bio', 'profile_picture', 'cover_picture', 'visibility_status', 'city', 'country', 'state',
            'awards', 'tools', 'notify_email', 'wall_tutorial', 'profile_tutorial', 'onboarding_required',
            ]
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
    is_following = serializers.SerializerMethodField()
    friend_request_status = serializers.SerializerMethodField()
    got_friend_request = serializers.SerializerMethodField()
    organized_events = serializers.SerializerMethodField()

    city_name = serializers.CharField(source='city.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)

    
    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'bio', 'profile_picture', 'cover_picture',
            'profile_type', 'visibility_status',
            'followers_count', 'following_count', 'friends_count',
            'field_sections', 'is_friend', 'is_following', 'friend_request_status', 'static_sections',
            'got_friend_request', 'organized_events', 'website_url', 'tiktok_url', 'youtube_url', 'linkedin_url',
            'instagram_url', 'twitter_url', 'facebook_url', 'city_name', 'state_name', 'country_name', 'awards', 'tools',
            'notify_email', 'profile_tutorial', 'wall_tutorial', 'onboarding_required'
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
    
    def get_is_following(self, obj):
        """
        Check if the request user's profile is following with the target profile.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        try:
            user_profile = get_user_profile(request.user)
            return obj in user_profile.following.all()
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
        context = self.context.copy()
        context['profile'] = obj
        serializer = StaticProfileSectionSerializer(sections, many=True, context=context)
        return serializer.data
    
    def get_organized_events(self, obj):
        events = obj.organized_events.all()
        return EventListSerializer(events, many=True).data 


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
    field_value = serializers.CharField(allow_blank=True, required=False, allow_null=True)

    def validate_static_field_id(self, value):
        if not StaticProfileField.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid static_field_id.")
        return value

    def validate(self, attrs):
        static_field_id = attrs.get('static_field_id')
        field_value = attrs.get('field_value')
        
        try:
            static_field = StaticProfileField.objects.get(id=static_field_id)
        except StaticProfileField.DoesNotExist:
            raise serializers.ValidationError("Invalid static_field_id.")
        
        # Validate based on field type
        if static_field.field_type == StaticFieldType.DATE and field_value:
            try:
                # Try to parse the date
                datetime.strptime(field_value, '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError("Invalid date format. Use YYYY-MM-DD.")
        
        elif static_field.field_type == StaticFieldType.NUMBER and field_value:
            try:
                Decimal(field_value)
            except InvalidOperation:
                raise serializers.ValidationError("Invalid number format.")
        
        elif static_field.field_type == StaticFieldType.BOOLEAN and field_value:
            if field_value.lower() not in ['true', 'false', '1', '0']:
                raise serializers.ValidationError("Boolean value must be 'true', 'false', '1', or '0'.")
        
        elif static_field.field_type == StaticFieldType.EMAIL and field_value:
            email_validator = serializers.EmailField()
            try:
                email_validator.run_validation(field_value)
            except serializers.ValidationError:
                raise serializers.ValidationError("Invalid email format.")
        
        elif static_field.field_type == StaticFieldType.URL and field_value:
            url_validator = serializers.URLField()
            try:
                url_validator.run_validation(field_value)
            except serializers.ValidationError:
                raise serializers.ValidationError("Invalid URL format.")
        
        # Check required fields
        if static_field.is_required and not field_value:
            raise serializers.ValidationError(f"Field '{static_field.field_name}' is required.")
        
        attrs['static_field'] = static_field
        return attrs


class ArtServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtService
        exclude = ['profile']


class ArtServiceInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtServiceInquiry
        fields = ['id', 'artist_profile', 'inquirer_profile', 'message', 'created_at']
        read_only_fields = ['id', 'created_at', 'inquirer_profile']


class ProfileSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'username', 'bio', 'profile_picture', 'tools', 'awards']
