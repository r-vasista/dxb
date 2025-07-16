from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import random
from datetime import timedelta
from django.db import transaction

from notification.models import Notification,DailyQuote, DailyQuoteSeen


from core.services import send_dynamic_email_using_template,get_user_profile


def send_notification_email(recipient, sender, message, notification_type):
    user = getattr(recipient, 'user', None) or getattr(getattr(recipient, 'organization', None), 'user', None)

    if user and user.email and recipient.notify_email:
        context = {
            "user_name": recipient.username,
            "message": message,
            "notification_type": notification_type,
            "sender_username": sender.username,
        }
        template_name = "generic-notification"
        try:
            send_dynamic_email_using_template(template_name, [user.email], context)
        except Exception:
            pass

        
def create_notification(*args):
    """
    Flexible notification creator:
    Supports both:
      - (sender, recipient, instance, message, notification_type)
      - (obj, sender, recipient, instance, message, notification_type)
    """
    if len(args) == 5:
        sender, recipient, instance, message, notification_type = args
    elif len(args) == 6:
        _, sender, recipient, instance, message, notification_type = args
    else:
        raise TypeError("create_notification() takes 5 or 6 positional arguments")

    notification = Notification(
        sender=sender,
        recipient=recipient,
        notification_type=notification_type,
        message=message
    )
    if instance:
        notification.content_type = ContentType.objects.get_for_model(instance)
        notification.object_id = instance.id
    notification.save()

    if recipient.notify_email:
        transaction.on_commit(lambda: send_notification_email(recipient, sender, message, notification_type))


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
    if instance:
        notification.content_type = ContentType.objects.get_for_model(instance)
        notification.object_id = instance.id

    try :
        if recipient.notify_email:
            context = {
                "user_name": get_user_profile(recipient).username,
                "message": message,
                "notification_type": notification_type,
                "sender_username": sender.username,
            }
            
            template_name = "generic-notification"  # Make sure this matches your EmailTemplate DB entry
            send_dynamic_email_using_template(template_name, [user.email], context)
    except:
        pass

    notification.save()

