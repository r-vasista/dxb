from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from user.models import Permission  # your custom model

class Command(BaseCommand):
    help = 'Create custom permissions in custom Permission model'

    def handle(self, *args, **kwargs):
        permissions = [
            # (code, description, app_label, model, type, scope, is_visible)
            ('view_org_prof_field', '', 'organization', 'organizationprofilefield', 'view', 'organization', True),
            ('create_org_prof_field', '', 'organization', 'organizationprofilefield', 'create', 'organization', True),
            ('update_org_prof_field', '', 'organization', 'organizationprofilefield', 'update', 'organization', True),
            ('delete_org_prof_field', '', 'organization', 'organizationprofilefield', 'delete', 'organization', True),
            ('update_org', '', 'organization', 'organization', 'update', 'organization', True),
            ('delete_org', '', 'organization', 'organization', 'delete', 'organization', True),
            ('create_org_invite', '', 'organization', 'organizationinvite', 'create', 'organization', True),
            ('view_org_invite', '', 'organization', 'organizationinvite', 'view', 'organization', True),
            ('view_org_member', '', 'organization', 'organizationmember', 'view', 'organization', True),
        ]

        for code, description, app_label, model_name, type_, scope, is_visible in permissions:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model_name)
                perm, created = Permission.objects.get_or_create(
                    code=code,
                    defaults={
                        'description': description,
                        'content_type': ct,
                        'type': type_,
                        'scope': scope,
                        'is_visible': is_visible
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created permission: {code}'))
                else:
                    self.stdout.write(f'Permission already exists: {code}')
            except ContentType.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'ContentType not found for: {app_label}.{model_name}'))
