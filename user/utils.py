from django.core import signing
from datetime import timedelta
from django.utils import timezone

import re
import uuid
from django.utils.text import slugify
from django.db import IntegrityError
from profiles.models import Profile, ProfileType
from user.models import Role, UserType

TOKEN_EXPIRY_MINUTES = 15

def generate_registration_token(email):
    payload = {
        "email": email,
        "exp": (timezone.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)).timestamp()
    }
    return signing.dumps(payload)

def verify_registration_token(token):
    try:
        data = signing.loads(token, max_age=TOKEN_EXPIRY_MINUTES * 60)
        if data["exp"] < timezone.now().timestamp():
            return None  # Expired
        return data["email"]
    except signing.BadSignature:
        return None
    except signing.SignatureExpired:
        return None

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


USERNAME_SAFE_RE = re.compile(r"[^a-z0-9_.-]+")

def make_username_base(full_name: str, email: str) -> str:
    base = slugify(full_name or email.split("@")[0] or "user")
    base = USERNAME_SAFE_RE.sub("", base)
    return (base or "user")

def generate_unique_username(full_name: str, email: str) -> str:
    base = make_username_base(full_name, email)
    candidate = base
    i = 0
    while Profile.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
        if i > 50:
            candidate = f"{base}-{uuid.uuid4().hex[:6]}"
            break
    return candidate

def get_or_create_user_type(code: str, name: str):
    return UserType.objects.get_or_create(code=code, defaults={"name": name})[0]

def ensure_role(user, role_name: str):
    role, _ = Role.objects.get_or_create(name=role_name)
    user.roles.add(role)
