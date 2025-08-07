# Rest Framework imports
from rest_framework import serializers

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupJoinRequest
)
from group.choices import (
    RoleChoices
)
from profiles.serializers import (
    BasicProfileSerializer
)


class GroupCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'type', 'description', 'logo', 'cover_image', 'privacy']

    def validate_name(self, value):
        if Group.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("A group with this name already exists.")
        return value


class GroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description', 'logo', 'cover_image']
        
        
class GroupDetailSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer()
    my_role = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    
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

    
class GroupPostSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    
    class Meta:
        model = GroupPost

class GroupPostCommentSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()

    class Meta:
        model = GroupPostComment
        fields = [
            'id', 'group_post', 'profile', 'content', 'parent',
            'created_at', 'reply_count', 'is_reply', 'like_count'
        ]
        read_only_fields = [
            'id', 'group_post', 'profile', 'created_at', 'reply_count', 'is_reply'
        ]

    def get_profile(self, obj):
        return {
            "id": obj.profile.id,
            "username": obj.profile.username,
            "profile_picture": obj.profile.profile_picture.url if getattr(obj.profile, "profile_picture", None) else None,
        }

    def get_reply_count(self, obj):
        return obj.reply_count

    def get_is_reply(self, obj):
        return obj.is_reply


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
        fields = ['id', 'profile', 'role', 'joined_at', 'is_banned']
      
        
class GroupListSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer(read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'logo', 'cover_image', 'creator', 'created_at']


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
