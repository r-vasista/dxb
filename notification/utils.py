from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import random
from datetime import timedelta

from notification.models import Notification,DailyQuote, DailyQuoteSeen


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


def get_random_unseen_quote_for_today(profile):
    today = timezone.localdate()

    today_seen = DailyQuoteSeen.objects.filter(
        profile=profile,
        created_at__date=today
    ).first()

    if today_seen:
        if not today_seen.email_sent and profile.notify_email:
            send_daily_muse_email(profile, today_seen.quote)
            today_seen.email_sent = True
            today_seen.save()
            return today_seen.quote, today_seen.created_at, False  # False means was not already emailed
        return today_seen.quote, today_seen.created_at, True  # ✅ already emailed today

    seen_ids = DailyQuoteSeen.objects.filter(profile=profile).values_list('quote_id', flat=True)
    unseen_quotes = DailyQuote.objects.exclude(id__in=seen_ids)

    if unseen_quotes.exists():
        quote = random.choice(list(unseen_quotes))
        seen_record = DailyQuoteSeen.objects.create(profile=profile, quote=quote)

        if profile.notify_email:
            send_daily_muse_email(profile, quote)
            seen_record.email_sent = True
            seen_record.save()

        return quote, seen_record.created_at, False  # newly created, not emailed before

    return None, None, False


def send_daily_muse_email(profile, quote):
    user = getattr(profile, 'user', None)
    if not user and hasattr(profile, 'organization'):
        user = getattr(profile.organization, 'user', None)

    if user and user.email:
        context = {
            "user_name": profile.username,
            "message": quote.text,
            "notification_type": "daily_muse",
            "sender_username": "Daily Muse"
        }
        template_name = "generic-notification"
        send_dynamic_email_using_template(template_name, [user.email], context)