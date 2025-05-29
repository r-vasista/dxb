from django.core.cache import cache
import random

def generate_otp(email):
    otp = str(random.randint(1000, 9999))
    cache.set(f"otp:{email}", otp, timeout=300)
    return otp

def verify_otp(email, otp):
    saved_otp = cache.get(f"otp:{email}")
    return saved_otp == otp

def delete_otp(email):
    cache.delete(f"otp:{email}")