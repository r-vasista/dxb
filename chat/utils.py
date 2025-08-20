from django.db.models import Q
from django.db import transaction
from chat.models import ChatGroup, ChatGroupMember, ChatMessage
from chat.choices import ChatType

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
