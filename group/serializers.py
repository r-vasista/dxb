# Rest Framework imports
from rest_framework import serializers

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
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
        fields = ['name', 'type', 'description', 'logo', 'cover_image']

    def validate_name(self, value):
        if Group.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("A group with this name already exists.")
        return value


class GroupDetailSerializer(serializers.ModelSerializer):
    creator = BasicProfileSerializer()
    my_role = serializers.SerializerMethodField()
    
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

    
class GroupPostSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    
    class Meta:
        model = GroupPost

class GroupPostCommentSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = GroupPostComment
        fields = ['id', 'group_post', 'profile', 'content', 'parent', 'like_count', 'reply_count', 'replies']

    def get_replies(self, obj):
        queryset = obj.replies.filter(is_active=True)
        return GroupPostCommentSerializer(queryset, many=True).data

class GroupPostLikeSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    class Meta:
        model = GroupPostLike
        fields = ['id', 'group_post', 'profile']

class GroupPostCommentLikeSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)
    class Meta:
        model = GroupPostCommentLike
        fields = ['id', 'comment', 'profile']


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