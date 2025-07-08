from django.contrib.contenttypes.models import ContentType
from notification.models import Notification
from core.services import send_dynamic_email_using_template,get_user_profile

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

NOTIFICATION_CONFIG = {
    'like': {
        'message': '{sender} liked your post',
        'get_recipient': lambda obj: obj.post.profile,
        'get_instance': lambda obj: obj.post,
    },
    'comment': {
        'message': '{sender} commented on your post',
        'get_recipient': lambda obj: obj.post.profile,
        'get_instance': lambda obj: obj.post
    },
    'follow': {
        'message': '{sender} started following you',
        'get_recipient': lambda obj: obj.following,
        'get_instance': lambda obj: None
    },
    'friend_request': {
        'message': '{sender} sent you a friend request',
        'get_recipient': lambda obj: obj.receiver,
        'get_instance': lambda obj: None
    },
    'friend_accept': {
        'message': '{sender} accepted your friend request',
        'get_recipient': lambda obj: obj.sender,
        'get_instance': lambda obj: None
    },

    'mention': {
        'message': '{sender} mentioned you',
        'get_recipient': lambda obj: obj.mentioned_user,
        'get_instance': lambda obj: obj.post
    },
    'share': {
        'message': '{sender} shared your post',
        'get_recipient': lambda obj: obj.original_post.profile,
        'get_instance': lambda obj: obj.original_post
    },
    'post_create': {
        'message': '{sender} created a new post',
        'get_recipient': lambda obj: obj.profile,  # Or followers
        'get_instance': lambda obj: obj
    }
}


def create_dynamic_notification(notification_type, obj, sender=None):
    config = NOTIFICATION_CONFIG.get(notification_type)

    if not config:
        raise ValueError(f"Notification type '{notification_type}' not supported.")

    recipient = config['get_recipient'](obj)
    print(recipient)
    if recipient.user:
        user=recipient.user
    else:
        user=recipient.organization.user
    instance = config['get_instance'](obj)
    sender = sender or getattr(obj, 'profile', None) or obj.get('sender', None)

    if not recipient or not sender:
        raise ValueError("Recipient or sender not found for notification.")

    message = config['message'].format(sender=sender.username)

    notification = Notification(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        message=message
    )
    print(user.email,'sdfg')
    if instance:
        notification.content_type = ContentType.objects.get_for_model(instance)
        notification.object_id = instance.id
    if recipient.notify_email:
        context = {
            "user_name": get_user_profile(recipient).username,
            "message": message,
            "notification_type": notification_type,
            "sender_username": sender.username,
        }
        
        template_name = "generic-notification"  # Make sure this matches your EmailTemplate DB entry
        send_dynamic_email_using_template(template_name, [user.email], context)
    

    notification.save()
