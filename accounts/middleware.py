"""
accounts/middleware.py - JWTAuthMiddleware

Reads the access_token httpOnly cookie on every request and sets request.user
so the rest of the app (templates, @login_required, etc.) works transparently.

If the access token is expired but a valid refresh token exists, it silently
generates a new access token and sets it in the response cookie.
"""
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin

from .jwt_utils import (
    decode_token,
    generate_tokens,
    get_user_from_access_token,
    set_auth_cookies,
)


class JWTAuthMiddleware(MiddlewareMixin):
    """Authenticate requests via JWT cookies instead of Django sessions."""

    def process_request(self, request):
        # If user is already authenticated (e.g., via Django admin session or test client)
        if getattr(request, "user", None) and request.user.is_authenticated:
            request._jwt_refresh_needed = False
            return

        # Fast path: valid access token in cookie
        user = get_user_from_access_token(request)
        if user is not None:
            request.user = user
            request._jwt_refresh_needed = False
            return

        # Access token missing/expired - try refresh
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            payload = decode_token(refresh_token)
            if payload and payload.get("token_type") == "refresh":
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(pk=payload["user_id"], is_active=True)
                    request.user = user
                    request._jwt_refresh_needed = True
                    request._jwt_refresh_user = user
                    return
                except (User.DoesNotExist, Exception):
                    pass

        # No valid tokens - ensure AnonymousUser if not already set
        if not getattr(request, "user", None):
            request.user = AnonymousUser()
        request._jwt_refresh_needed = False

    def process_response(self, request, response):
        # Silently set a fresh access token if refresh was used
        if getattr(request, "_jwt_refresh_needed", False):
            user = getattr(request, "_jwt_refresh_user", None)
            if user:
                tokens = generate_tokens(user)
                set_auth_cookies(response, tokens)
        return response
