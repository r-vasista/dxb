from django.db.models.signals import post_save
from django.dispatch import receiver
from post.models import Post

from core.services import send_dynamic_email_using_template


Milestone = [ 50, 100, 200, 500, 1000, 5000, 10000,  100000, 500000, 1000000, 5000000, 10000000, 50000000, 100000000, 500000000, 1000000000]

@receiver(post_save, sender=Post)
def post_save_handler(sender, instance, created, **kwargs):
    if created:
        return
    
    if instance.reaction.count in Milestone:
        profile=instance.profile
        user=getattr(profile, 'user', None)

        if not user and hasattr(profile, 'organization'):
            user = getattr(profile.organization, 'user', None)

        if user and user.email:
            context ={
                "user_name": profile.username,
                "post_title": instance.title or instance.content[:50],
                "like_count": instance.reactions.count,
                "notification_type": "post_milestone",
            }
        template = "post_milestone"
        send_dynamic_email_using_template(template, user.email, context)
