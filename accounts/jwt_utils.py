"""
accounts/jwt_utils.py - Pure-Python JWT helpers using PyJWT.

Token strategy:
  access_token  - short-lived (15 min), sent with every request via httpOnly cookie
  refresh_token - long-lived (7 days), used to silently renew the access token

Cookie flags:
  httponly=True  - JS cannot read -> prevents XSS token theft
  samesite=Lax   - safe against CSRF
  secure=False   - set True in production (HTTPS)
"""
import datetime

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

_ALGORITHM = "HS256"


def _secret():
    return getattr(settings, "JWT_SECRET", settings.SECRET_KEY)


def _access_expiry():
    minutes = getattr(settings, "JWT_ACCESS_EXPIRY_MINUTES", 15)
    return datetime.timedelta(minutes=minutes)


def _refresh_expiry():
    days = getattr(settings, "JWT_REFRESH_EXPIRY_DAYS", 7)
    return datetime.timedelta(days=days)


def generate_tokens(user):
    """Return a dict with access and refresh JWT strings for the given user."""
    now = datetime.datetime.now(datetime.timezone.utc)
    access_payload = {
        "token_type": "access",
        "user_id": user.pk,
        "username": user.username,
        "email": user.email,
        "iat": now,
        "exp": now + _access_expiry(),
    }
    refresh_payload = {
        "token_type": "refresh",
        "user_id": user.pk,
        "iat": now,
        "exp": now + _refresh_expiry(),
    }
    return {
        "access": jwt.encode(access_payload, _secret(), algorithm=_ALGORITHM),
        "refresh": jwt.encode(refresh_payload, _secret(), algorithm=_ALGORITHM),
    }


def decode_token(token):
    """Decode and verify a JWT. Returns payload dict or None if invalid/expired."""
    try:
        return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def set_auth_cookies(response, tokens, remember_me=False):
    """Write access + refresh JWTs into httpOnly cookies on the response."""
    refresh_days = 30 if remember_me else getattr(settings, "JWT_REFRESH_EXPIRY_DAYS", 7)
    response.set_cookie(
        "access_token",
        tokens["access"],
        max_age=int(_access_expiry().total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not getattr(settings, "DEBUG", True),
    )
    response.set_cookie(
        "refresh_token",
        tokens["refresh"],
        max_age=60 * 60 * 24 * refresh_days,
        httponly=True,
        samesite="Lax",
        secure=not getattr(settings, "DEBUG", True),
    )
    return response


def clear_auth_cookies(response):
    """Delete both auth cookies (logout)."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


def get_user_from_access_token(request):
    """Read the access_token cookie and return the corresponding User or None."""
    token = request.COOKIES.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("token_type") != "access":
        return None
    User = get_user_model()
    try:
        return User.objects.get(pk=payload["user_id"], is_active=True)
    except (User.DoesNotExist, Exception):
        return None
