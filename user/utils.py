from django.core import signing
from datetime import timedelta
from django.utils import timezone

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