# groups/signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import GroupMember
from chat.models import ChatGroup, ChatGroupMember


@receiver(post_delete, sender=GroupMember)
def remove_chat_member_on_group_remove(sender, instance, **kwargs):
    """
    Whenever a GroupMember is removed, 
    also remove them from the corresponding ChatGroupMember.
    """
    try:
        # Find ChatGroup for this Group
        chat_group = ChatGroup.objects.filter(group=instance.group).first()
        if chat_group:
            ChatGroupMember.objects.filter(
                group=chat_group,
                profile=instance.profile
            ).delete()
    except Exception as e:
        pass
