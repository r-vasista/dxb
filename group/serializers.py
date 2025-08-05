# Rest Framework imports
from rest_framework import serializers

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
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