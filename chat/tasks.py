from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from celery import shared_task
from chat.serializers import ChatMessageSerializer
from chat.models import ScheduleMessage, ChatMessage
from chat.consumers import group_room_name

@shared_task
def deliver_scheduled_message(scheduled_message_id):
    try:
        scheduled = ScheduleMessage.objects.get(id=scheduled_message_id, executed=False)
        profile = scheduled.sender
        group = scheduled.group

        # Create actual ChatMessage
        msg = ChatMessage.objects.create(
            group=group,
            sender=profile,
            message_type=scheduled.message_type,
            content=scheduled.content or "",
            file=scheduled.file
        )

        # Mark scheduled as executed
        scheduled.executed = True
        scheduled.save(update_fields=["executed"])

        channel_layer = get_channel_layer()
        data = ChatMessageSerializer(msg, context={"request": None}).data

        async_to_sync(channel_layer.group_send)(
            group_room_name(str(group.id)),
            {"type": "chat.message", "data": data}
        )
    except ScheduleMessage.DoesNotExist:
        return
