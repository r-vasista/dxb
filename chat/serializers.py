from rest_framework import serializers
from chat.models import ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt, ScheduleMessage
from chat.choices import ChatType
from profiles.serializers import BasicProfileSerializer  
from group.serializers import BasicGroupDetailSerializer
from core.services import get_user_profile
from core.serializers import TimezoneAwareSerializerMixin


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
    
    
class ChatMessageReceiptializer(serializers.ModelSerializer):
    user = BasicProfileSerializer(read_only=True)

    class Meta:
        model = MessageReceipt
        fields = ["user", "is_seen", "seen_at"]


class ChatMessageSerializer(TimezoneAwareSerializerMixin):
    sender = BasicProfileSerializer(read_only=True)
    receipts = ChatMessageReceiptializer(many=True, read_only=True)
    group = serializers.UUIDField(source="group.id", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "group", "sender", "message_type", "content", "file", "created_at", "edited_at", "is_deleted", "receipts",
                  "updated_at", "is_edited"]
        read_only_fields = ["id", "sender", "created_at", "edited_at", "is_deleted", "group", "receipts", "updated_at", "is_edited"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = "This message was deleted"
            data["file"] = None

        return data


class ChatMessageMiniSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    sender_is_me = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["id", "message_type", "content", "sender", "sender_is_me", "created_at"]

    def get_sender(self, obj):
        return {
            "id": obj.sender.id,
            "username": obj.sender.username,
        }

    def get_sender_is_me(self, obj):
        request = self.context.get("request")
        consumer_profile = self.context.get("profile")
        if consumer_profile and obj.sender_id == consumer_profile.id:
            return True
        if request and request.user.is_authenticated:
            profile = get_user_profile(request.user)
            return obj.sender_id == profile.id
        return False


class ChatGroupMiniSerializer(TimezoneAwareSerializerMixin):
    chat_id = serializers.UUIDField(source="group.id", read_only=True)
    type = serializers.CharField(source="group.type", read_only=True)
    counterpart = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField()
    is_muted = serializers.BooleanField()
    last_message = ChatMessageMiniSerializer(source="group.last_message", read_only=True)

    class Meta:
        model = ChatGroupMember
        fields = [
            "chat_id", "type", "counterpart",
            "unread_count", "is_muted", "last_message", "last_read_at"
        ]

    def get_counterpart(self, obj):
        g = obj.group
        if g.type == ChatType.PERSONAL:
            me = self.context["profile"]
            other = next(
                (m.profile for m in g.memberships.all() if m.profile_id != me.id),
                None
            )
            if other:
                return BasicProfileSerializer(other, context=self.context).data
        return None


class ScheduleMessageSerializer(TimezoneAwareSerializerMixin):
    class Meta:
        model = ScheduleMessage
        fields = ["id", "group", "sender", "message_type", "content", "file", "scheduled_at", "executed"]
        read_only_fields = ["id", "sender", "executed"]

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user.profile
        return super().create(validated_data)
