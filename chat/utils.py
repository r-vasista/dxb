from django.db.models import Q
from django.db import transaction
from chat.models import ChatGroup, ChatGroupMember, ChatMessage
from chat.choices import ChatType
from chat.serializers import ChatGroupSerializer
from profiles.models import Profile
from profiles.serializers import BasicProfileSerializer


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def get_or_create_personal_group(profile_a, profile_b):
    """
    Returns an existing personal group for these two profiles or creates a new one.
    """
    if profile_a.id == profile_b.id:
        raise ValueError("Cannot create a personal chat with yourself.")

    # Try to find existing personal group with exactly these two members
    candidate_groups = ChatGroup.objects.filter(type=ChatType.PERSONAL)
    candidate_groups = candidate_groups.filter(
        memberships__profile=profile_a
    ).filter(
        memberships__profile=profile_b
    ).distinct()

    group = candidate_groups.first()
    if group:
        # sanity: ensure only two members for personal chat
        return group

    with transaction.atomic():
        # Check if they are friends
        if not profile_a.friends.filter(id=profile_b.id).exists():
            raise PermissionError("You can only start a personal chat with friends.")
        group = ChatGroup.objects.create(type=ChatType.PERSONAL)
        ChatGroupMember.objects.bulk_create([
            ChatGroupMember(group=group, profile=profile_a),
            ChatGroupMember(group=group, profile=profile_b),
        ])
    return group


def is_group_member(group, profile):
    return group.memberships.filter(profile=profile).exists()


def broadcast_active_chats_update(profile_id):
    """
    Notify ActiveChatsConsumer for this user to refresh active chats.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"active_chats_{profile_id}",
        {"type": "active_chats_update"}
    )
    
async def async_broadcast_active_chats_update(profile_id):
    """
    Async version: call this from consumers.
    """
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"active_chats_{profile_id}",
        {"type": "active_chats_update"}
    )

def get_chat_counterpart_ids(profile_id):
    """
    Given a profile_id, return all profile_ids of users
    who share at least one chat with this profile.
    """
    group_ids = ChatGroupMember.objects.filter(profile_id=profile_id)\
                                       .values_list("group_id", flat=True)
    counterpart_ids = ChatGroupMember.objects.filter(group_id__in=group_ids)\
                                             .exclude(profile_id=profile_id)\
                                             .values_list("profile_id", flat=True)\
                                             .distinct()
    return list(counterpart_ids)

def async_broadcast_presence_update(profile, is_online):
    channel_layer = get_channel_layer()
    group_ids = list(
        ChatGroupMember.objects.filter(profile=profile)
        .values_list("group_id", flat=True)
    )

    # All counterparts (other profiles in these groups)
    counterpart_ids = (
        ChatGroupMember.objects.filter(group_id__in=group_ids)
        .exclude(profile_id=profile.id)
        .values_list("profile_id", flat=True)
        .distinct()
    )

    # Prepare payload (once)
    for pid in counterpart_ids:
        try:
            counterpart = Profile.objects.select_related("user").get(id=pid)

            serialized_profile = BasicProfileSerializer(
                profile,
                context={"user": counterpart.user}
            ).data

            payload = {
                "type": "presence.update",
                "data": {
                    "profile": serialized_profile,
                    "is_online": is_online,
                }
            }

            # 1. Send to counterpart's sidebar
            async_to_sync(channel_layer.group_send)(
                f"active_chats_{pid}", payload
            )
        except Profile.DoesNotExist:
            continue

    # 2. Send once per shared group
    for gid in group_ids:
        async_to_sync(channel_layer.group_send)(
            f"chat_{gid}",
            {"type": "chat.presence", "data": payload["data"]}
        )
