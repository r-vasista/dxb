from rest_framework import serializers
from chat.models import ChatGroup, ChatGroupMember, ChatMessage
from profiles.serializers import BasicProfileSerializer  
from group.serializers import BasicGroupDetailSerializer


class ChatGroupMemberSerializer(serializers.ModelSerializer):
    profile = BasicProfileSerializer(read_only=True)

    class Meta:
        model = ChatGroupMember
        fields = ["profile", "joined_at", "is_muted", "last_read_at"]


class ChatGroupSerializer(serializers.ModelSerializer):
    group = BasicGroupDetailSerializer()
#     members = serializers.SerializerMethodField()

    class Meta:
        model = ChatGroup
        fields = ["id", "type", "group", "created_at", "last_message_at"]

    # def get_members(self, obj):
    #     qs = obj.memberships.select_related("profile__user")
    #     return ChatGroupMemberSerializer(qs, many=True, context=self.context).data


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = BasicProfileSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "group", "sender", "message_type", "content", "file", "created_at", "edited_at", "is_deleted"]
        read_only_fields = ["id", "sender", "created_at", "edited_at", "is_deleted", "group"]
