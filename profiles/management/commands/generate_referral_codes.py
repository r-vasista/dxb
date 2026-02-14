import uuid
from django.core.management.base import BaseCommand
from profiles.models import Profile

class Command(BaseCommand):
    help = "Generate unique referral codes for all profiles that don't have one"

    def handle(self, *args, **options):
        updated_count = 0
        for profile in Profile.objects.filter(referral_code__isnull=True):
            code = str(uuid.uuid4()).split("-")[0].upper()
            # Ensure uniqueness
            while Profile.objects.filter(referral_code=code).exists():
                code = str(uuid.uuid4()).split("-")[0].upper()
            profile.referral_code = code
            profile.save(update_fields=["referral_code"])
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Referral codes generated for {updated_count} profiles.")
        )
