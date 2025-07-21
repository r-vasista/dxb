from datetime import timedelta
import logging
import random
from celery import shared_task


from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from requests import post
from django.db import transaction

from core.services import send_dynamic_email_using_template,get_actual_user
from core.utils import get_user
from event.models import Event, EventAttendance, EventComment, EventMedia, EventMediaComment
from profiles.models import Profile, ProfileView
from notification.models import DailyQuote, DailyQuoteSeen, Notification  
from notification.choices import NotificationType
from post.models import PostReaction,Comment ,Post, PostView,SharePost
from profiles.models import FriendRequest
from notification.utils import create_notification, send_notification_email
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
    if reaction.post.profile == reaction.profile:
        logger.info(f"Sender and recipient are the same. Skipping notification for {reaction.profile.username} on post {reaction.post.id}")
        return

    recipient = reaction.post.profile
    sender = reaction.profile
    instance = reaction.post
    notification_type = NotificationType.LIKE
    reaction_name = reaction.reaction_type.lower().capitalize()  # e.g., "Like", "Love"
    message = f"{sender.username} hit your post with a {reaction_name}"

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
    if comment.post.profile == comment.profile:
        logger.info(f"Sender and recipient are the same. Skipping notification for {comment.profile.username} on post {comment.post.id}")
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
        message = f"{profile.username} has created a new post."
        logger.info(f"Notifying friend {friend.username} about new post by {profile.username}")
        create_notification(profile, friend, post, message, notification_type)

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


@shared_task
def send_weekly_profile_stats():
    one_week_ago = timezone.now() - timedelta(days=7)
    now = timezone.now()

    profiles = Profile.objects.filter(notify_email=True)

    for profile in profiles:
        user = get_user(profile)
        email_to = user.email

        # Stats from the last 7 days
        posts_created = Post.objects.filter(profile=profile, created_at__range=(one_week_ago, now)).count()
        likes_received = PostReaction.objects.filter(post__profile=profile, created_at__range=(one_week_ago, now)).count()
        likes_given = PostReaction.objects.filter(profile=profile, created_at__range=(one_week_ago, now)).count()
        comments_made = Comment.objects.filter(profile=profile, created_at__range=(one_week_ago, now)).count()
        comments_received = Comment.objects.filter(post__profile=profile, created_at__range=(one_week_ago, now)).count()
        shares = SharePost.objects.filter(profile=profile, created_at__range=(one_week_ago, now)).count()
        profile_views = ProfileView.objects.filter(profile=profile, created_at__range=(one_week_ago, now)).count()
        post_views = PostView.objects.filter(post__profile=profile, created_at__range=(one_week_ago, now)).count()

        context = {
            "name": profile.username,
            "posts_created": posts_created,
            "likes_received": likes_received,
            "likes_given": likes_given,
            "comments_made": comments_made,
            "comments_received": comments_received,
            "shares": shares,
            # "followers": profile.followers.count(),
            "following": profile.following.count(),
            "friends": profile.friends.count(),
            "profile_views": profile_views,
            "post_views": post_views,
            "date_range": f"{one_week_ago.date()} to {now.date()}",
        }

        # Send email
        send_dynamic_email_using_template(
            template_name="weekly-profile-stats",
            recipient_list=[email_to],
            context=context,
        )

@shared_task
def send_event_creation_notification_task(event_id):
    """
    Send notifications to all followers when an event is created.
    """
    try:
        event = Event.objects.select_related('host').get(id=event_id)
        sender = event.host
        message = f"{sender.username} created a new event: {event.title}"
        notification_type = NotificationType.EVENT_CREATE

        followers = sender.followers.all()
        logger.info(f"Sending notifications to {followers.count()} followers for event {event_id}")

        for follower in followers:
            try:
                create_notification(
                    sender=sender,
                    recipient=follower,
                    instance=event,
                    message=message,
                    notification_type=notification_type
                )
            except Exception as inner_e:
                logger.error(
                    f"[send_event_creation_notification_task] Failed to notify {follower.username}: {inner_e}",
                    exc_info=True
                )

        logger.info(f"[send_event_creation_notification_task] Notifications sent for event {event_id}")

    except Event.DoesNotExist:
        logger.warning(f"[send_event_creation_notification_task] Event with id {event_id} not found.")
    except Exception as e:
        logger.error(
            f"[send_event_creation_notification_task] Error sending notifications: {str(e)}",
            exc_info=True
        )

@shared_task
def send_event_rsvp_notification_task(attendance_id):
    try:
        attendance = EventAttendance.objects.select_related('event', 'profile').get(id=attendance_id)
        event = attendance.event
        attendee = attendance.profile
        host = event.host

        attendance_count = EventAttendance.objects.filter(event=event).count()

        if host != attendee:
            message = (f"""{attendee.username} RSVP'd to your event: {event.title}.
                       with status: {attendance.status.title()}
                        Total attendees so far: {attendance_count}"""
                    )
            create_notification(
                sender=attendee,
                recipient=host,
                instance=event,
                message=message,
                notification_type=NotificationType.EVENT_RSVP
            )
        message_to_attendee = (
            f"Thank you {attendee.username} for RSVPing to '{event.title}'.\n"
            f"Your status: {attendance.status.title()}\n"
            f"Event Host: {host.username}"
        )
        create_notification(
            sender=host,
            recipient=attendee,
            instance=event,
            message=message_to_attendee,
            notification_type=NotificationType.EVENT_RSVP
        )

        logger.info(f"RSVP notification sent for Event ID: {event.id}")
    except EventAttendance.DoesNotExist:
        logger.warning(f"Attendance with id {attendance_id} not found")
    except Exception as e:
        logger.error(f"Error sending RSVP notification: {e}", exc_info=True)

@shared_task
def send_event_media_notification_task(event_id, uploader_id, media_id):
    try:
        event = Event.objects.get(id=event_id)
        uploader = Profile.objects.get(id=uploader_id)
        attendees = EventAttendance.objects.filter(event=event).select_related('profile')
        media = EventMedia.objects.get(id=media_id)

        for attendance in attendees:
            recipient = attendance.profile
            if recipient != uploader:
                message = f"{uploader.username} uploaded new media to the event: {event.title}."
                create_notification(
                    sender=uploader,
                    recipient=recipient,
                    instance=event,
                    message=message,
                    notification_type=NotificationType.EVENT_MEDIA
                )

        if uploader == event.host:
            host_msg = f"You shared new event media with all attendees of {event.title}."
            create_notification(
                sender=uploader,
                recipient=uploader,
                instance=event,
                message=host_msg,
                notification_type=NotificationType.EVENT_MEDIA
            )

    except Exception as e:
        logger.error(f"Error sending media upload notifications: {e}", exc_info=True)


@shared_task
def shared_event_media_comment_notification_task(event_media_id, profile_id, comment_id):
    try:
        # Fetch all required objects
        event_media = EventMedia.objects.select_related('event', 'event__host__user').get(id=event_media_id)
        profile = Profile.objects.select_related('user').get(id=profile_id)
        comment = EventMediaComment.objects.select_related('parent', 'parent__profile__user').get(id=comment_id)

        event = event_media.event
        event_host = event.host

        sender_user = get_actual_user(profile)
        host_user = get_actual_user(event_host)


        # Notify the event host (if host is not the commenter)
        if host_user and sender_user and host_user != sender_user:
            message = f"{profile.username} commented on your event media."
            logger.info(f"Sending notification to event host: {event_host.username}")
            create_notification(
                sender=profile,
                recipient=event_host,
                instance=comment,
                message=message,
                notification_type=NotificationType.COMMENT
            )

        # Notify the parent comment author (if it's a reply and not self)
        if comment.parent:
            parent_profile = comment.parent.profile
            parent_user = get_actual_user(parent_profile)

            if parent_user and sender_user != parent_user:
                message = f"{profile.username} replied to your comment."
                logger.info(f"Sending reply notification to parent commenter: {parent_profile.username}")
                create_notification(
                    sender=profile,
                    recipient=parent_profile,
                    instance=comment,
                    message=message,
                    notification_type=NotificationType.COMMENT
                )

    except ObjectDoesNotExist as e:
        logger.warning(f"[MediaCommentNotify] Object not found: {e}")
    except Exception as e:
        logger.error(f"[MediaCommentNotify] Unexpected error: {e}", exc_info=True)


@shared_task
def send_event_reminder_notifications():
    try:
        now = timezone.now()

        target_24h = now + timedelta(hours=24)
        target_3h = now + timedelta(hours=3)

        window_24h_start = target_24h.replace(minute=0, second=0, microsecond=0)
        window_24h_end = window_24h_start + timedelta(minutes=59, seconds=59)

        window_3h_start = target_3h.replace(minute=0, second=0, microsecond=0)
        window_3h_end = window_3h_start + timedelta(minutes=59, seconds=59)

        reminder_windows = {
            'reminder_1st_sent': (window_24h_start, window_24h_end),  # 24 hours
            'reminder_2nd_sent': (window_3h_start, window_3h_end),    # 3 hours
        }

        for reminder_flag, (start_time, end_time) in reminder_windows.items():
            events = Event.objects.filter(
                start_datetime__range=(start_time, end_time),
                status='published'
            )

            for event in events:
                attendees = EventAttendance.objects.filter(event=event).select_related('profile')

                for attendance in attendees:
                    if getattr(attendance, reminder_flag):
                        continue  

                    profile = attendance.profile
                    hours = "24" if reminder_flag == "reminder_1st_sent" else "3"
                    message = f"Reminder: '{event.title}' starts in {hours} hours."

                    create_notification(
                        sender=event.host,
                        recipient=profile,
                        instance=event,
                        message=message,
                        notification_type=NotificationType.EVENT_REMINDER
                    )

                    setattr(attendance, reminder_flag, True)
                    attendance.save(update_fields=[reminder_flag])

    except Exception as e:
        logger.error(f"Error sending event reminders: {e}", exc_info=True)



