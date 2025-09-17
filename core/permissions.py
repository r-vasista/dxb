
# Local imports
from organization.models import OrganizationMember

def is_owner_or_org_member(profile, user):
    is_allowed = False

    # Case 1: Individual profile
    if profile.user and profile.user == user:
        is_allowed = True

    # Case 2: Organization profile
    elif profile.organization:
        org = profile.organization

        # Check if user is the org owner
        if org.user == user:
            is_allowed = True
        # Check if user is a member of the org
        elif OrganizationMember.objects.filter(organization=org, user=user).exists():
            is_allowed = True
    
    return is_allowed