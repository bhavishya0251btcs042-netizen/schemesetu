"""accounts/urls.py - URL routes for the authentication app."""
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("auth/signup/", views.signup_view, name="signup"),
    path("auth/signup/verify/", views.otp_verify_view, name="otp_verify"),
    path("auth/signup/resend-otp/", views.resend_otp_view, name="resend_otp"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/profile/", views.profile_view, name="profile"),
    path("auth/token/refresh/", views.token_refresh_view, name="token_refresh"),
]
