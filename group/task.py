from celery import shared_task
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.db import transaction

from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q

from notification.task_monitor import monitor_task
from profiles.models import Profile
from group.models import (Group ,GroupMember, GroupPost, GroupPostComment, GroupPostCommentLike, GroupPostLike, GroupActionLog)
from group.choices import RoleChoices,JoiningRequestStatus
from notification.choices import NotificationType
from notification.models import Notification
from notification.utils import create_notification  
from core.services import send_dynamic_email_using_template,get_actual_user

from event.models import Event
import logging

logger = logging.getLogger(__name__)




@shared_task
def send_group_creation_notifications_task(group_id, profile_id):
    try:
        logger.info(f"Task started: Sending group creation notifications for group {group_id}, profile {profile_id}")
        
        # 1. Fetch Group
        try:
            group = Group.objects.get(id=group_id)
            logger.info(f"Loaded group: {group.name} (ID: {group_id})")
        except Group.DoesNotExist:
            print(f"Group {group_id} not found.")
            return

        # 2. Fetch Profile and User
        try:
            profile = Profile.objects.select_related('user').get(id=profile_id)
            logger.info(f"Loaded profile: {profile.username} (ID: {profile_id})")
        except Profile.DoesNotExist:
            logger.warning(f"Profile {profile_id} not found.")
            return

        user = getattr(profile, 'user', None)
        if not user or not user.email:
            logger.warning(f"User or email missing for profile {profile_id}. User: {user}")
            return

        # 3. Prepare owner email context
        context = {
            'user_name': profile.username,
            'group_name': group.name,
            'group_description': getattr(group, 'description', ''),
            'invite_url': f"https://yourfrontend.com/groups/{group.id}/invite",
            'share_post_url': f"https://yourfrontend.com/groups/{group.id}/share",
            'roles': {
                'ADMIN': 'Admin',
                'MODERATOR': 'Moderator',
                'CONTRIBUTOR': 'Contributor',
                'Viewer': 'Viewer'
            }
        }

        # 4. Send email to group owner
        try:
            status, msg = send_dynamic_email_using_template('group-creation-email.html', [user.email], context)
            logger.info(f"Group creation email sent to owner {user.email} for group {group_id}")
        except Exception as e:
            logger.error(f"Failed to send owner email: {e}", exc_info=True)

        # 5. Fetch friends/followers
        followers = []
        if hasattr(profile, 'friends'):
            try:
                followers = profile.friends.all()
                logger.info(f"Found {followers.count()} friends/followers for user {profile.username}")
            except Exception as e:
                logger.error(f"Error retrieving friends for user {profile.username}: {e}", exc_info=True)
        else:
            logger.warning(f"User {profile.username} has no 'friends' attribute.")

        # 6. Process followers: notifications + email list
        follower_emails = []
        for follower in followers:
            try:
                create_notification(
                    sender=profile,
                    recipient=follower,
                    instance=group,
                    message=f"{profile.username} created a new group: {group.name}. Join and start sharing!",
                    notification_type=NotificationType.Group
                )
                logger.info(f"Notification created for {follower.username}")

                follower_user = getattr(follower, 'user', None)
                if follower_user and follower_user.email:
                    follower_emails.append(follower_user.email)
                    logger.info(f"Follower email added: {follower_user.email}")
                else:
                    logger.warning(f"No email found for follower {follower.username}")

            except Exception as e:
                logger.error(f"Failed to handle follower {follower.username}: {e}", exc_info=True)

        # 7. Send follower emails
        if follower_emails:
            follower_context = {
                'group_name': group.name,
                'creator_name': profile.username,
                'invite_url': context['invite_url'],
                'message': f"{profile.username} has created a new group '{group.name}'. You are invited to join and contribute!",
            }
            try:
                send_dynamic_email_using_template('group-created-follower-email.html', follower_emails, follower_context)
                logger.info(f"Sent group creation emails to {len(follower_emails)} followers of {profile.username}")
            except Exception as e:
                logger.error(f"Failed to send follower emails: {e}", exc_info=True)
        else:
            logger.info(f"No follower emails to send for group {group_id}")

    except Exception as e:
        logger.error(f"Error in send_group_creation_notifications_task: {e}", exc_info=True)



# tasks.py
@shared_task
def send_group_join_notifications_task(group_id, profile_id, action='joined',sender_id=None):
    try:
        group = Group.objects.get(id=group_id)
        profile = Profile.objects.select_related('user').get(id=profile_id)
        user = profile.user
        sender= Profile.objects.select_related('user').get(id=sender_id)

        # Define message
        if action == 'joined':
            member_message = f"You've successfully joined the group '{group.name}'."
            admin_message = f"{profile.username} has joined the group '{group.name}'."
        elif action == 'accepted':
            member_message = f"Your request to join '{group.name}' has been accepted!"
            admin_message = f"{profile.username}'s join request was accepted by {sender.username}."
        elif action == 'rejected':
            member_message = f"Your request to join '{group.name}' has been rejected."
            admin_message = f"{profile.username}'s join request was rejected by {sender.username}."
        elif action == 'removed':
            member_message = f"You have been removed from the group '{group.name}'."
            admin_message = f"{profile.username} was removed from the group by {sender.username}."
        elif action == 'updated':
            member_message = f"Your role in the group '{group.name}' has been updated."
            admin_message = f"{profile.username}'s role was updated by {sender.username}."
        else:
            logger.warning(f"Unknown action '{action}'")
            return

        # Notify the user (who joined/requested)
        create_notification(
            sender=sender,
            recipient=profile,
            instance=group,
            message=member_message,
            notification_type=NotificationType.Group if action in ['joined', 'accepted'] else NotificationType.Group
        )
        if user and user.email:
            send_dynamic_email_using_template(
                'group-join-user-email.html',
                [user.email],
                {
                    'user_name': profile.username,
                    'group_name': group.name,
                    'message': member_message,
                    'group_url': f"https://yourfrontend.com/groups/{group.id}"
                }
            )

        # Notify Admins/Moderators
        admins = GroupMember.objects.filter(group=group, role__in=[RoleChoices.ADMIN, RoleChoices.MODERATOR])
        for admin_member in admins:
            admin_profile = admin_member.profile
            admin_user = admin_profile.user
            Notification.objects.create(
                sender=profile,
                recipient=admin_profile,
                notification_type=NotificationType.Group,
                message=admin_message,
                content_type=ContentType.objects.get_for_model(group),
                object_id=group.id
            )


    except Exception as e:
        logger.error(f"Error in send_group_join_notifications_task: {e}", exc_info=True)


@shared_task
@monitor_task(task_name="send_inactivity_reminders_task", expected_interval_minutes=1440)
def send_inactivity_reminders_task():
    logger.info("Running: send_inactivity_reminders_task")
    cutoff_date = timezone.now() - timedelta(days=1)

    # Annotate groups with latest post date
    inactive_groups = Group.objects.annotate(
        last_post_date=Max('posts__created_at')
    ).filter(
        Q(last_post_date__lt=cutoff_date) | Q(last_post_date__isnull=True),
        is_active=True
    )

    for group in inactive_groups:
        admins = GroupMember.objects.filter(
            group=group,
            role__in=[RoleChoices.ADMIN, RoleChoices.MODERATOR]
        )

        reminder_message = (
            f"The group '{group.name}' has had no posts in the last 30 days. "
            "Encourage members to stay active!"
        )

        for admin_member in admins:
            admin_profile = admin_member.profile
            # Send notification (assumes your notification util)
            create_notification(
                sender=admin_profile,
                recipient=admin_profile,
                instance=group,
                message=reminder_message,
                notification_type=NotificationType.Group,
            )

            # Optionally send email if you have this function
            if admin_profile.user and admin_profile.user.email:
                send_dynamic_email_using_template(
                    'group-inactivity-reminder.html',
                    [admin_profile.user.email],
                    {
                        'group_name': group.name,
                        'admin_name': admin_profile.username,
                        'reminder_message': reminder_message,
                        'group_url': f"https://yourfrontend.com/groups/{group.id}"
                    }
                )


@shared_task
def notify_group_members_of_new_post(post_id):
    """Notify all group members when a new post is created in the group."""
    logger.info(f"[notify_group_members_of_new_post] Starting task for post_id={post_id}")

    try:
        post = GroupPost.objects.select_related('group', 'profile').get(id=post_id)
        logger.info(f"[notify_group_members_of_new_post] Found post ID {post.id} in group '{post.group.name}' by {post.profile.username}")
    except GroupPost.DoesNotExist:
        logger.warning(f"[notify_group_members_of_new_post] GroupPost with ID {post_id} not found.")
        return

    sender = post.profile
    group = post.group

    members = GroupMember.objects.filter(
        group=group,
        is_banned=False
    ).exclude(profile=sender).select_related('profile')

    member_count = members.count()
    logger.info(f"[notify_group_members_of_new_post] Found {member_count} members to notify (excluding sender).")

    if member_count == 0:
        logger.warning(f"[notify_group_members_of_new_post] No members to notify for group '{group.name}'.")
        return

    for member in members:
        recipient = member.profile
        logger.info(f"[notify_group_members_of_new_post] Notifying {recipient.username} (email: {recipient.user.email if hasattr(recipient, 'user') else 'N/A'})")

        message = f"{sender.username} created a new post in {group.name}."

        try:
            create_notification(
                sender=sender,
                recipient=recipient,
                instance=post,
                message=message,
                notification_type=NotificationType.Group
            )
            logger.info(f"[notify_group_members_of_new_post] Notification created for {recipient.username}")
        except Exception as e:
            logger.error(f"[notify_group_members_of_new_post] Failed to create notification for {recipient.username}: {str(e)}", exc_info=True)

    logger.info(f"[notify_group_members_of_new_post] Finished notifying members for post {post_id}")

@shared_task
def notify_owner_of_group_post_comment(comment_id):
    """
    Notify the owner of a group post when a new comment is added.
    """
    try:
        comment = GroupPostComment.objects.select_related(
            "group_post", "group_post__profile", "profile"
        ).get(id=comment_id)

        group_post = comment.group_post
        post_owner = group_post.profile

        # Don't notify if the commenter is the owner
        if post_owner != comment.profile:
            Notification.objects.create(
                sender=comment.profile,
                recipient=post_owner,
                instance=group_post,
                message=f"{comment.profile.username} commented on your group post.",
                notification_type=NotificationType.Group
            )
            logger.info(
                f"[notify_owner_of_group_post_comment] Sent to '{post_owner.username}' "
                f"for post ID {group_post.id}"
            )

    except GroupPostComment.DoesNotExist:
        logger.warning(f"[notify_owner_of_group_post_comment] Comment ID {comment_id} not found.")
    except Exception as e:
        logger.error(f"[notify_owner_of_group_post_comment] Error: {e}", exc_info=True)


@shared_task
def notify_owner_of_group_post_like(self, like_id):
    """
    Notify the owner of a group post when someone likes it.
    """
    try:
        like = GroupPostLike.objects.select_related("group_post", "group_post__profile", "profile").get(id=like_id)
        group_post = like.group_post
        post_owner = group_post.profile

        if post_owner != like.profile:
            Notification.objects.create(
                sender=like.profile,
                recipient=post_owner,
                instance=group_post,
                message=f"{like.profile.username} liked your group post.",
                notification_type=NotificationType.Group
            )
            logger.info(
                f"[notify_owner_of_group_post_like] Sent to '{post_owner.username}' for post ID {group_post.id}"
            )

    except GroupPostLike.DoesNotExist:
        logger.warning(f"[notify_owner_of_group_post_like] Like ID {like_id} not found.")
    except Exception as e:
        logger.error(f"[notify_owner_of_group_post_like] Error: {e}", exc_info=True)


@shared_task
def notify_owner_of_group_comment_like(comment_like_id):
    """
    Notify the owner of a group post comment when someone likes it.
    """
    try:
        comment_like = GroupPostCommentLike.objects.select_related(
            "comment", "comment__profile", "profile"
        ).get(id=comment_like_id)

        comment = comment_like.comment
        comment_owner = comment.profile

        if comment_owner != comment_like.profile:
            Notification.objects.create(
                sender=comment_like.profile,
                recipient=comment_owner,
                instance=comment,
                message=f"{comment_like.profile.username} liked your comment.",
                notification_type=NotificationType.Group
            )
            logger.info(
                f"[notify_owner_of_group_comment_like] Sent to '{comment_owner.username}' for comment ID {comment.id}"
            )

    except GroupPostCommentLike.DoesNotExist:
        logger.warning(f"[notify_owner_of_group_comment_like] CommentLike ID {comment_like_id} not found.")
    except Exception as e:
        logger.error(f"[notify_owner_of_group_comment_like] Error: {e}", exc_info=True)


@shared_task
@monitor_task(task_name="send_weekly_group_digest", expected_interval_minutes=10080)
def send_weekly_group_digest(event_id=None, debug=False, return_data=False):
    logger.info("Running: send_weekly_group_digest")
    one_week_ago = timezone.now() - timedelta(days=7)
    now = timezone.now()


    try:
        groups = Group.objects.all()

        for group in groups:
            # Top posts (past week)
            top_posts = (
                GroupPost.objects.filter(group=group, created_at__range=(one_week_ago, now))
                .annotate(total_likes=Count("post_likes"))
                .order_by("-total_likes")[:5]
            )

            # Top contributors
            top_contributors = (
                GroupPost.objects.filter(group=group, created_at__range=(one_week_ago, now))
                .values("profile__username")
                .annotate(post_count=Count("id"))
                .order_by("-post_count")[:5]
            )

            # Upcoming events
            upcoming_events = (
                Event.objects.filter(start_datetime__gte=now)
                .order_by("start_datetime")[:5]
            )

            # Admin members with email notifications enabled
            admin_members = Profile.objects.filter(
                id__in=GroupMember.objects.filter(
                    group=group, role=RoleChoices.ADMIN
                ).values_list("profile_id", flat=True),
                notify_email=True
            )



            def send_emails_and_notify():
                for member in admin_members:
                    user = get_actual_user(member)
                    if not user or not user.email:
                        continue

                    context = {
                        "group_name": group.name,
                        "member_name": member.username,
                        "top_posts": top_posts,
                        "top_contributors": top_contributors,
                        "upcoming_events": upcoming_events,
                        "date_range": f"{one_week_ago.date()} to {now.date()}",
                    }

                    try:
                        status, msg = send_dynamic_email_using_template(
                            template_name="weekly-group-digest",
                            recipient_list=[user.email],
                            context=context,
                        )
                        print(f"{status} - {msg}")
                    except Exception as e:
                        logger.error(
                            f"[send_weekly_group_digest] Failed to send digest to {member.username} ({user.email}): {e}",
                            exc_info=True
                        )

            if not return_data:
                transaction.on_commit(send_emails_and_notify)

    except Exception as e:
        logger.error(f"[send_weekly_group_digest] Unexpected error: {e}", exc_info=True)


@shared_task
@monitor_task(task_name="delete_old_group_action_logs", expected_interval_minutes=1440)
def delete_old_group_action_logs():
    """
    Deletes GroupActionLog records older than 10 days.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=10)
        deleted_count, _ = GroupActionLog.objects.filter(created_at__lt=cutoff_date).delete()

        logger.info(f"Deleted {deleted_count} old group action logs older than 10 days.")
        return {"status": True, "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error deleting old group action logs: {str(e)}", exc_info=True)
        return {"status": False, "error": str(e)}