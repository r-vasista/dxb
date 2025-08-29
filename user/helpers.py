from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings

class GoogleTokenError(Exception):
    pass

def verify_google_id_token(token: str) -> dict:
    """
    Verifies Google ID token and returns the payload.
    Raises GoogleTokenError if invalid.
    """
    try:
        request = requests.Request()
        # Verify token signature & expiry
        payload = id_token.verify_oauth2_token(token, request)
    except Exception as e:
        raise GoogleTokenError(f"Invalid Google ID token: {e}")

    # Validate issuer
    issuers = set(settings.GOOGLE_OAUTH.get("ISSUERS", []))
    if payload.get("iss") not in issuers:
        raise GoogleTokenError("Invalid issuer.")

    # Validate audience against your allowed client IDs
    client_ids = set(settings.GOOGLE_OAUTH.get("CLIENT_IDS", []))
    aud = payload.get("aud")
    print('payload', payload)
    print('aud', aud)
    # if aud not in client_ids:
    #     raise GoogleTokenError("Invalid audience (client_id mismatch).")

    # Must have verified email
    if not payload.get("email_verified"):
        raise GoogleTokenError("Email not verified with Google.")

    # Optional: restrict hosted domain
    # allowed_hd = set(settings.GOOGLE_OAUTH.get("HOSTED_DOMAINS", []))
    # if allowed_hd:
    #     if payload.get("hd") not in allowed_hd:
    #         raise GoogleTokenError("Unauthorized Google Workspace domain.")

    return payload
