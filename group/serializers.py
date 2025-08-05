# Rest Framework imports
from rest_framework import serializers

# Local imports
from group.models import (
    Group, GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike
)


class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'type', 'description', 'logo', 'cover_image']

    def validate_name(self, value):
        if Group.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("A group with this name already exists.")
        return value