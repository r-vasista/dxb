from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_params = parse_qs(scope["query_string"].decode())
        token = query_params.get("token")
        
        if token:
            try:
                access_token = AccessToken(token[0])
                user = await self.get_user(access_token)
                scope["user"] = user
            except Exception:
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)

    @staticmethod
    async def get_user(access_token):
        try:
            user = await User.objects.aget(id=access_token["user_id"])
            return user
        except User.DoesNotExist:
            return AnonymousUser()
