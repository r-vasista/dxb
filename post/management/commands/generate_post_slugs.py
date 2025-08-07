from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils.timezone import now
from post.models import Post
from core.services import (get_user_profile)

class Command(BaseCommand):
    help = 'Ensure all posts have unique slugs based on title, username, and date.'

    def handle(self, *args, **options):
        updated_count = 0
        MAX_SLUG_BASE_LENGTH =20
        for post in Post.objects.all():
            original_slug = post.slug
            username = post.profile.username if post.created_by else 'unknown'
            created_date = post.created_at or now()
            date_part = created_date.strftime("%Y%m%d%H%M%S")
            base_slug = slugify(f"{post.title.strip()[:MAX_SLUG_BASE_LENGTH]}-{username}-{date_part}")
            slug = base_slug

            # Ensure uniqueness
            if Post.objects.filter(slug=slug).exclude(id=post.id).exists():
                timestamp_suffix = created_date.strftime('%H%M%S%f')
                slug = slugify(f"{base_slug}-{timestamp_suffix}")

            if post.slug != slug:
                post.slug = slug
                post.save(update_fields=['slug'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated Post ID {post.id}: {original_slug} → {slug}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Done. {updated_count} posts updated."))
