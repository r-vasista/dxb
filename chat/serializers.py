from rest_framework import serializers
from chat.models import ChatGroup, ChatGroupMember, ChatMessage, MessageReceipt, ScheduleMessage, ChatTheme
from chat.choices import ChatType
from profiles.serializers import BasicProfileSerializer  
from group.serializers import BasicGroupDetailSerializer
from core.services import get_user_profile
from core.serializers import TimezoneAwareSerializerMixin
from post.serializers import PostSerializer, BasicPostSerializer
from event.serializers import EventDetailSerializer, EventMediaSerializer
from group.serializers import GroupPostSerializer


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
    shared_post = serializers.SerializerMethodField()
    shared_event = serializers.SerializerMethodField()
    shared_group_post = serializers.SerializerMethodField()
    shared_event_media = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["id", "group", "sender", "message_type", "content", "file", "shared_post", "shared_event", "created_at", "edited_at", "is_deleted", "receipts",
                  "updated_at", "is_edited",  "shared_group_post", "shared_event_media"]
        read_only_fields = ["id", "sender", "created_at", "edited_at", "is_deleted", "group", "receipts", "updated_at", "is_edited"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = "This message was deleted"
            data["file"] = None

        return data
    
    def get_shared_post(self, obj):
        if obj.shared_post:
            return BasicPostSerializer(obj.shared_post, context=self.context).data
        return None
    
    def get_shared_event(self, obj):
        if obj.shared_event:
            return EventDetailSerializer(obj.shared_event, context=self.context).data
        return None

    def get_shared_group_post(self, obj):
        if obj.shared_group_post:
            return GroupPostSerializer(obj.shared_group_post, context=self.context).data
        return None

    def get_shared_event_media(self, obj):
        if obj.shared_event_media:
            return EventMediaSerializer(obj.shared_event_media, context=self.context).data
        return None


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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = "This message was deleted"
        return data



class ChatGroupMiniSerializer(TimezoneAwareSerializerMixin):
    chat_id = serializers.UUIDField(source="group.id", read_only=True)
    type = serializers.CharField(source="group.type", read_only=True)
    counterpart = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField()
    is_muted = serializers.BooleanField()
    last_message = serializers.SerializerMethodField()
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
                # Ensure timezone context is available
                ctx = dict(self.context)
                if "user" not in ctx:
                    ctx["user"] = me.user
                return BasicProfileSerializer(other, context=ctx).data
        return None
    
    def get_last_message(self, obj):
        profile = self.context["profile"]

        # Exclude messages deleted for this profile
        qs = (
            ChatMessage.objects
            .filter(group=obj.group)
            .exclude(deletions__profile=profile)
            .order_by("-created_at")
        )

        msg = qs.first()
        return ChatMessageMiniSerializer(msg, context=self.context).data if msg else None


class ScheduleMessageSerializer(TimezoneAwareSerializerMixin):
    class Meta:
        model = ScheduleMessage
        fields = ["id", "group", "sender", "message_type", "content", "file", "scheduled_at", "executed"]
        read_only_fields = ["id", "sender", "executed"]

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user.profile
        return super().create(validated_data)


class ChatThemeSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = ChatTheme
        fields = '__all__'
