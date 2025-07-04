from django.contrib.contenttypes.models import ContentType
from notification.models import Notification

def create_notification(sender, recipient, notification_type, message, instance=None):
    if sender == recipient:
        return 

    notification = Notification(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        message=message
    )

    if instance:
        notification.content_type = ContentType.objects.get_for_model(instance.__class__)
        notification.object_id = instance.pk

    notification.save()
    return notification

def create_post_reaction_notification(post_reaction):
    
    create_notification(
        sender=post_reaction.profile,
        recipient=post_reaction.post.profile,
        notification_type='like',
        message=f'{post_reaction.profile.username} liked your post',
        instance=post_reaction.post
    )