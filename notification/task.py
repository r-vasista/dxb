import logging
import random
from celery import shared_task


from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from requests import post


from core.services import send_dynamic_email_using_template
from profiles.models import Profile
from notification.models import DailyQuote, DailyQuoteSeen, Notification  
from notification.choices import NotificationType
from post.models import PostReaction,Comment ,Post,SharePost
from profiles.models import FriendRequest
from notification.utils import create_notification
# Setup logger
logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email_task(profile_id):
    try:
        profile = Profile.objects.select_related('user', 'organization').get(id=profile_id)
    except ObjectDoesNotExist:
        logger.warning(f"Profile with ID {profile_id} not found.")
        return

    user = getattr(profile, 'user', None)
    if not user and hasattr(profile, 'organization'):
        user = getattr(profile.organization, 'user', None)

    if user and user.email:
        context = {
            'user_name': profile.username,
        }
        template_name = 'welcome-email'
        try:
            send_dynamic_email_using_template(template_name, [user.email], context)
            logger.info(f"✅ Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"❌ Failed to send email to {user.email}: {e}")
    else:
        logger.warning(f"❌ No valid user or email found for profile ID {profile_id}")


@shared_task
def send_daily_muse_to_all_profiles():
    profiles = Profile.objects.filter(notify_email=True)

    for profile in profiles:
        try:
            today = timezone.localdate()
            today_seen = DailyQuoteSeen.objects.filter(profile=profile, created_at__date=today).first()

            if today_seen:
                if not today_seen.email_sent and profile.notify_email:
                    send_daily_muse_email(profile, today_seen.quote)
                    today_seen.email_sent = True
                    today_seen.save()
                    logger.info(f"✅ Sent today's Daily Muse to profile {profile.id}")
                else:
                    logger.info(f"✅ Daily Muse already sent today to profile {profile.id}")
                continue

            # Get unseen quotes
            seen_ids = DailyQuoteSeen.objects.filter(profile=profile).values_list('quote_id', flat=True)
            unseen_quotes = DailyQuote.objects.exclude(id__in=seen_ids)

            if unseen_quotes.exists():
                quote = random.choice(list(unseen_quotes))
                seen_record = DailyQuoteSeen.objects.create(profile=profile, quote=quote)

                if profile.notify_email:
                    send_daily_muse_email(profile, quote)
                    seen_record.email_sent = True
                    seen_record.save()
                    logger.info(f"✅ Sent new Daily Muse to profile {profile.id}")
            else:
                logger.warning(f"⚠️ No unseen quotes left for profile {profile.id}")

        except Exception as e:
            logger.exception(f"❌ Exception while sending Daily Muse to profile {profile.id}")



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


# tasks.py
@shared_task
def send_post_reaction_notification_task(reaction_id):
    """ Sends a notification when a user reacts to a post.
    """
    try:
        reaction = PostReaction.objects.select_related('post', 'post__profile', 'profile').get(id=reaction_id)
    except ObjectDoesNotExist:
        logger.warning(f"PostReaction with ID {reaction_id} not found.")
        return

    recipient = reaction.post.profile
    sender = reaction.profile
    instance = reaction.post
    notification_type = NotificationType.LIKE
    reaction_name = reaction.reaction_type.lower().capitalize()  # e.g., "Like", "Love"
    message = f"{sender.username} reacted ({reaction_name}) to your post"

    if recipient and sender:
        logger.info(f"Sending reaction notification: {message} to {recipient.username} from {sender.username}")
        create_notification(reaction, sender, recipient, instance, message, notification_type)


@shared_task
def send_comment_notification_task(comment_id):
    """ Sends a notification when a user comments on a post. """
    try:
        comment = Comment.objects.select_related('post', 'post__profile', 'profile').get(id=comment_id)
    except ObjectDoesNotExist:
        logger.warning(f"Comment with ID {comment_id} not found.")
        return

    recipient = comment.post.profile
    sender = comment.profile
    instance = comment.post
    notification_type = NotificationType.COMMENT
    message = f"{sender.username} commented on your post"

    if recipient and sender:
        logger.info(f"Sending comment notification: {message} to {recipient.username} from {sender.username}")
        create_notification(comment, sender, recipient, instance, message, notification_type)

@shared_task
def send_friend_request_notification_task(friend_request_id):
    """Sends a notification when a friend request is sent."""
    try:
        friend_request = FriendRequest.objects.select_related('from_profile', 'to_profile').get(id=friend_request_id)
    except ObjectDoesNotExist:
        logger.warning(f"FriendRequest with ID {friend_request_id} not found.")
        return

    sender = friend_request.from_profile
    recipient = friend_request.to_profile
    notification_type = NotificationType.FRIEND_REQUEST
    message = f"{sender.username} sent you a friend request"

    if sender and recipient:
        logger.info(f"Sending friend request notification: {message} to {recipient.username} from {sender.username}")
        create_notification(sender, recipient, friend_request, message, notification_type)

@shared_task
def send_friend_request_response_notification_task(friend_request_id, response_type):
    """
    Sends a notification when a friend request is accepted.
    """
    try:
        friend_request = FriendRequest.objects.select_related('from_profile', 'to_profile').get(id=friend_request_id)
    except ObjectDoesNotExist:
        logger.warning(f"FriendRequest with ID {friend_request_id} not found.")
        return

    if response_type != "accepted":
        return  # Ignore anything else, only accept is supported here

    sender = friend_request.to_profile      # The one who accepted
    recipient = friend_request.from_profile # The one who sent the request
    message = f"{sender.username} accepted your friend request"
    notification_type = NotificationType.FRIEND_ACCEPTED
    create_notification(sender, recipient, friend_request, message, notification_type)
    """
    Sends a notification when a friend request is accepted or rejected.
    """
    try:
        friend_request = FriendRequest.objects.select_related('from_profile', 'to_profile').get(id=friend_request_id)
    except ObjectDoesNotExist:
        return

    sender = friend_request.to_profile  
    recipient = friend_request.from_profile  

    if response_type == "accepted":
        message = f"{sender.username} accepted your friend request"
        notification_type = NotificationType.FRIEND_ACCEPTED
    else:
        message = f"{sender.username} rejected your friend request"
        notification_type = NotificationType.FRIEND_REQUEST_REJECTED
    logger.info(f"Sending friend request response notification: {message} to {recipient.username} from {sender.username}")
    create_notification(sender, recipient, friend_request, message, notification_type)



@shared_task
def notify_friends_of_new_post(post_id):
    """ Notifies friends of a user when a new post is created. """
    try:
        post = Post.objects.select_related('profile').get(id=post_id)
    except ObjectDoesNotExist:
        logger.warning(f"Post with ID {post_id} not found.")
        return

    profile = post.profile
    friends = profile.friends.all()
    notification_type = NotificationType.POST_CREATE

    for friend in friends:
        if friend.notify_email:
            message = f"{profile.username} has created a new post."
            logger.info(f"Notifying friend {friend.username} about new post by {profile.username}")
            create_notification(profile, friend, post, message, notification_type)
        else:
            logger.info(f"Friend {friend.username} has email notifications disabled, skipping notification for new post.")

@shared_task
def send_post_share_notification_task(share_id):
    """ Sends a notification when a post is shared. """
    try:
        share = SharePost.objects.select_related('post', 'post__profile', 'profile').get(id=share_id)
    except ObjectDoesNotExist:
        logger.warning(f"SharePost with ID {share_id} not found.")
        return

    sender = share.profile
    recipient = share.post.profile
    instance = share.post
    notification_type = NotificationType.SHARE
    message = f"{sender.username} shared your post"

    if sender != recipient:
        logger.info(f"Sending share notification: {message} to {recipient.username} from {sender.username}")
        create_notification(sender, recipient, instance, message, notification_type)


@shared_task
def send_mention_notification_task(from_profile_id, to_profile_id, post_id):
    try:
        sender = Profile.objects.get(id=from_profile_id)
        recipient = Profile.objects.get(id=to_profile_id)
        post = Post.objects.get(id=post_id)
        notification_type = NotificationType.MENTION

        if sender != recipient and recipient.allow_mentions:
            message = f"{sender.username} mentioned you in a post"
            create_notification(post, sender, recipient, post, message, notification_type)
            logger.info(f"✅ Mention notification sent to {recipient.username}")
    except ObjectDoesNotExist:
        logger.warning("❌ Mention task failed — object not found.")
    except Exception as e:
        logger.error(f"❌ Mention task error: {e}")