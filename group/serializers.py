from rest_framework import serializers

from group.models import GroupPost

from profiles.serializers import BasicProfileSerializer

class GroupPostSerializer(serializers.ModelSerializer):
    profile=BasicProfileSerializer(read_only=True)
    class Meta:
        model = GroupPost
        fields = '__all__'