# Rest Framework imports
from rest_framework import serializers

#Django imports 
from django.utils import timezone

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupJoinRequest, GroupPostFlag,
     GroupActionLog
)
from group.choices import (
    RoleChoices
)
from group.utils import (
    handle_grouppost_hashtags
)
from profiles.serializers import (
    BasicProfileSerializer
)
from core.serializers import HashTagSerializer
from core.services import get_user_profile
from core.models import (
    HashTag
)

class GroupCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'type', 'description', 'logo', 'cover_image', 'privacy', 'slug', 'privacy', 'show_members']

class GroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description', 'logo', 'cover_image', 'privacy', 'show_members']
        
        
class GroupDetailSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer()
    my_role = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = '__all__'

    def get_my_role(self, obj):
        """Show role if user is authenticated and is a member."""
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            try:
                member = GroupMember.objects.get(group=obj, profile=request.user.profile)
                return member.role
            except GroupMember.DoesNotExist:
                return None
        return None
    
    def get_join_request_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                join_request = GroupJoinRequest.objects.get(group=obj, profile=request.user.profile)
                if join_request.status in ['pending', 'accepted']:
                    return {
                        "id": join_request.id,
                        "status": join_request.status
                    }
            except GroupJoinRequest.DoesNotExist:
                pass
        return None
    
    def get_is_owner(self, obj):
        """Show role if user is authenticated and is a member."""
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            try:
                return obj.creator == request.user.profile
            except:
                return None
        return None

    
class  GroupPostSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    tags = HashTagSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    class Meta:
        model = GroupPost
        fields = [
            'id', 'group', 'profile', 'content', 'media_file', 'tags',
            'is_announcement', 'announcement_expiry', 'likes_count',
            'comments_count', 'share_count', 'is_flagged', 'flag_count',
            'slug'
        ]
        read_only_fields =['slug']
        extra_kwargs = {
            'is_pinned': {'default': False}  # Ensures default False
        }
    def get_comments_count(self, obj):
        return GroupPostComment.objects.filter(
            group_post=obj,
            is_active=True,
            parent__isnull=True  # ✅ Count only top-level comments
        ).count()


class GroupPostCommentSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField(read_only=True)
    reply_count = serializers.SerializerMethodField(read_only=True)
    is_reply = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GroupPostComment
        fields = [
            'id', 'group_post', 'profile', 'content', 'parent',
            'created_at', 'reply_count', 'is_reply', 'like_count'
        ]
        read_only_fields = [
            'id', 'group_post', 'profile', 'created_at', 'reply_count', 'is_reply', 'like_count'
        ]

    def get_profile(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if getattr(obj.profile, "profile_picture", None) else None,
        }

    def get_reply_count(self, obj):
        return obj.replies.filter(is_active=True).count()

    def get_is_reply(self, obj):
        return obj.parent is not None

    def create(self, validated_data):
        return GroupPostComment.objects.create(**validated_data)

    

class GroupPostLikeSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    class Meta:
        model = GroupPostLike
        fields = ['id', 'group_post', 'profile','created_at']


class GroupPostCommentLikeSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    class Meta:
        model = GroupPostCommentLike
        fields = ['id', 'comment', 'profile','created_at']


class AddGroupMemberSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=RoleChoices.choices)
    
    class Meta:
        model = GroupMember
        fields = '__all__'
        read_only_fields = ['assigned_by']
        extra_kwargs = {
            'role': {'required': True}
        }
        validators = []

    def validate(self, data):
        group = self.context.get('group')
        profile = data['profile']

        if GroupMember.objects.filter(group=group, profile=profile).exists():
            raise serializers.ValidationError("This profile is already a member of the group.")

        return data


class GroupMemberSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ['id', 'profile', 'role', 'joined_at', 'is_banned', 'activity_score']
      
        
class GroupListSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name','slug', 'description', 'logo', 'cover_image', 'creator', 'created_at', 'my_role',
                  'privacy', 'join_request_status',
                  ]
    
    def get_my_role(self, obj):
        """Show role if user is authenticated and is a member."""
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            try:
                member = GroupMember.objects.get(group=obj, profile=request.user.profile)
                return member.role
            except GroupMember.DoesNotExist:
                return None
        return None
    
    def get_join_request_status(self, obj):
        """Return the join request status for the current user if exists."""
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            try:
                join_request = GroupJoinRequest.objects.get(group=obj, profile=request.user.profile)
                return join_request.status
            except GroupJoinRequest.DoesNotExist:
                return None
        return None


class GroupMemberUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=RoleChoices.choices)

    class Meta:
        model = GroupMember
        fields = ['role']
        

class GroupJoinRequestSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)

    class Meta:
        model = GroupJoinRequest
        fields = ['id', 'group', 'profile', 'status', 'message', 'created_at']
        read_only_fields = ['id', 'group', 'profile', 'status', 'created_at']


class GroupActionLogSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    profile = BasicProfileSerializer(read_only=True)

    class Meta:
        model = GroupActionLog
        fields = [
            "id", "group", "group_name", "profile",
            "action", "description", "group_post", "group_member", "member_request",
            "created_at"
        ]

class GroupPostFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPostFlag
        fields = ["id", "post", "reported_by", "reason", "description", "created_at"]
        read_only_fields = ["id", "post", "reported_by", "created_at"]
    
class GroupPostFlagListSerializer(serializers.ModelSerializer):
    post = GroupPostSerializer(read_only=True)
    reported_by = BasicProfileSerializer(read_only=True)

    class Meta:
        model = GroupPostFlag
        fields = '__all__'

class GroupSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'slug', 'type', 'description',
            'tags', 'creator', 'privacy', 'logo', 'cover_image',
            'member_count', 'post_count', 'avg_engagement',
            'trending_score', 'last_activity_at', 'featured'
        ]
        read_only_fields = fields


class GroupSuggestionSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "logo",
            "cover_image",
            "creator",
            "member_count",
            "post_count",
            "trending_score",
            "featured",
        ]
        

class BasicGroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'slug', 'cover_image', 'logo']
        

class GroupPostUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=HashTag.objects.all(), many=True, required=False
    )

    class Meta:
        model = GroupPost
        fields = ['content', 'tags', 'is_pinned', 'is_announcement', 'announcement_expiry']
        
    def update(self, instance, validated_data):
        request = self.context.get("request")
        profile = get_user_profile(request.user)

        # Tags
        if "tags" in validated_data:
            tags = validated_data.pop("tags", [])
            instance.tags.set(tags)

        # Handle pinning logic
        if "is_pinned" in validated_data:
            pin_requested = validated_data.pop("is_pinned")
            group_member = GroupMember.objects.filter(
                group=instance.group, profile=profile, is_banned=False
            ).first()
            allowed_roles = [RoleChoices.ADMIN, RoleChoices.MODERATOR]
            is_privileged = group_member and group_member.role in allowed_roles

            if not is_privileged:
                raise serializers.ValidationError("Only admins/moderators can pin posts.")

            if pin_requested:
                if not instance.is_pinned or instance.is_pin_expired():
                    instance.is_pinned = True
                    instance.pinned_at = timezone.now()
                else:
                    raise serializers.ValidationError("Post is already pinned and not expired.")
            else:
                instance.is_pinned = False
                instance.pinned_at = None

        if "is_announcement" in validated_data:
            instance.is_announcement = validated_data["is_announcement"]

        if "announcement_expiry" in validated_data:
            instance.announcement_expiry = validated_data["announcement_expiry"]

        # Content update
        instance.content = validated_data.get("content", instance.content)

        instance.save()

        # Handle hashtags
        handle_grouppost_hashtags(instance)

        return instance