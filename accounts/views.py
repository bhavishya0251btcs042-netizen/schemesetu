"""
accounts/views.py - Authentication views: signup (2-step OTP), login, logout, profile.

Signup flow:
  1. GET/POST /auth/signup/        -> SignupForm; on valid POST stores data in session,
                                      generates OTP, shows it on the verify page
  2. POST     /auth/signup/verify/ -> OTPVerifyForm; on valid OTP creates User,
                                      sets JWT cookies, redirects to home

Login flow:
  POST /auth/login/ -> authenticates user, sets JWT cookies, redirects to next/home

Logout:
  GET /auth/logout/ -> clears JWT cookies, redirects to login
"""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import LoginForm, OTPVerifyForm, SignupForm
from .jwt_utils import (
    clear_auth_cookies,
    decode_token,
    generate_tokens,
    set_auth_cookies,
)
from .models import OTPRecord

User = get_user_model()

# Session keys
_PENDING_SIGNUP_KEY = "pending_signup"
_PENDING_OTP_EMAIL_KEY = "pending_otp_email"


# ---------------------------------------------------------------------------
# SIGNUP — Step 1
# ---------------------------------------------------------------------------

def signup_view(request):
    """Collect signup data, generate OTP, store in session, redirect to verify."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            email = cd["email"]

            # Invalidate any previous OTP for this email
            OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)

            # Generate fresh OTP and persist to DB
            otp_record = OTPRecord.objects.create(email=email)

            # Stash signup data in session (NOT in DB yet - user not verified)
            request.session[_PENDING_SIGNUP_KEY] = {
                "name": cd["name"],
                "username": cd["username"],
                "email": email,
                "phone": cd.get("phone", ""),
                "password": cd["password1"],
            }
            request.session[_PENDING_OTP_EMAIL_KEY] = email
            request.session.modified = True

            # Redirect cleanly to OTP verification page
            return redirect("accounts:otp_verify")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


# ---------------------------------------------------------------------------
# SIGNUP — Step 2: OTP verification
# ---------------------------------------------------------------------------

def otp_verify_view(request):
    """Verify OTP, create User account, set JWT cookies."""
    if request.user.is_authenticated:
        return redirect("core:home")

    email = request.session.get(_PENDING_OTP_EMAIL_KEY)
    pending = request.session.get(_PENDING_SIGNUP_KEY)

    if not email or not pending:
        messages.error(request, "Signup session expired or not found. Please start registration again.")
        return redirect("accounts:signup")

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data["otp_code"]

            # Fetch latest unused, unexpired OTP for this email
            otp_record = (
                OTPRecord.objects
                .filter(email=email, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if otp_record is None:
                messages.error(request, "OTP not found. Please request a new one.")
            elif otp_record.is_expired:
                messages.error(request, "OTP has expired (valid for 10 minutes). Please click 'Resend OTP'.")
                otp_record.mark_used()
            elif otp_record.otp_code != entered_otp:
                messages.error(request, "Incorrect OTP. Please check the code displayed above and try again.")
            else:
                # OTP correct — create the user
                otp_record.mark_used()
                first_name = pending["name"].split()[0] if pending["name"] else ""
                last_name = " ".join(pending["name"].split()[1:]) if " " in pending["name"] else ""

                try:
                    user = User.objects.create_user(
                        username=pending["username"],
                        email=pending["email"],
                        password=pending["password"],
                        first_name=first_name,
                        last_name=last_name,
                    )
                except Exception as e:
                    messages.error(request, f"Registration error: {e}")
                    return render(request, "accounts/otp_verify.html", {
                        "form": form,
                        "demo_otp": otp_record.otp_code,
                        "email": email,
                    })

                # Clean up session
                request.session.pop(_PENDING_SIGNUP_KEY, None)
                request.session.pop(_PENDING_OTP_EMAIL_KEY, None)
                request.session.modified = True

                messages.success(
                    request,
                    f"Welcome to SchemeSetu, {user.first_name or user.username}! "
                    "Your account is verified and you are now logged in."
                )

                # Set JWT cookies and redirect home
                tokens = generate_tokens(user)
                response = redirect("core:home")
                set_auth_cookies(response, tokens)
                return response

        # Validation failed — redisplay verify page with the current demo OTP
        otp_record = OTPRecord.objects.filter(email=email, is_used=False).order_by("-created_at").first()
        demo_otp = otp_record.otp_code if otp_record else "------"
        return render(request, "accounts/otp_verify.html", {
            "form": form,
            "demo_otp": demo_otp,
            "email": email,
        })

    # GET — show verify page (after redirect from signup_view, but no POST data)
    if request.GET.get("resend") == "1":
        OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
        otp_record = OTPRecord.objects.create(email=email)
        messages.info(request, "A new OTP has been generated.")
    else:
        otp_record = OTPRecord.objects.filter(email=email, is_used=False).order_by("-created_at").first()

    demo_otp = otp_record.otp_code if otp_record else "------"
    return render(request, "accounts/otp_verify.html", {
        "form": OTPVerifyForm(),
        "demo_otp": demo_otp,
        "email": email,
    })


# ---------------------------------------------------------------------------
# OTP RESEND
# ---------------------------------------------------------------------------

def resend_otp_view(request):
    """Invalidate old OTP and create a fresh one for the pending email."""
    email = request.session.get(_PENDING_OTP_EMAIL_KEY)
    if not email:
        messages.error(request, "Signup session expired. Please start again.")
        return redirect("accounts:signup")

    OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
    OTPRecord.objects.create(email=email)

    messages.info(request, "A new OTP has been generated.")
    return redirect("accounts:otp_verify")


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------

def login_view(request):
    """Authenticate user and issue JWT cookies."""
    if request.user.is_authenticated:
        return redirect(request.GET.get("next") or "core:home")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            identifier = cd["username"].strip()
            password = cd["password"]
            remember_me = cd.get("remember_me", False)

            # Support login with email OR username
            user = authenticate(request, username=identifier, password=password)
            if user is None:
                # Try email lookup
                try:
                    db_user = User.objects.get(email__iexact=identifier)
                    user = authenticate(request, username=db_user.username, password=password)
                except User.DoesNotExist:
                    pass

            if user is not None and user.is_active:
                messages.success(
                    request,
                    f"Welcome back, {user.first_name or user.username}!"
                )
                tokens = generate_tokens(user)
                next_url = request.POST.get("next") or request.GET.get("next") or "core:home"
                response = redirect(next_url)
                set_auth_cookies(response, tokens, remember_me=remember_me)
                return response
            else:
                messages.error(request, "Invalid username/email or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {
        "form": form,
        "next": request.GET.get("next", ""),
    })


# ---------------------------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------------------------

def logout_view(request):
    """Clear JWT cookies and redirect to login."""
    messages.info(request, "You have been logged out successfully.")
    response = redirect("accounts:login")
    clear_auth_cookies(response)
    return response


# ---------------------------------------------------------------------------
# PROFILE
# ---------------------------------------------------------------------------

def profile_view(request):
    """Display logged-in user profile. Redirects to login if not authenticated."""
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your profile.")
        return redirect(f"/auth/login/?next=/auth/profile/")

    user = request.user
    return render(request, "accounts/profile.html", {"user": user})


# ---------------------------------------------------------------------------
# SILENT TOKEN REFRESH (called by JS or redirect)
# ---------------------------------------------------------------------------

def token_refresh_view(request):
    """
    Silently refresh the access token using the refresh cookie.
    Returns 200 on success, 401 if refresh token invalid/expired.
    """
    from django.http import JsonResponse

    refresh_token = request.COOKIES.get("refresh_token")
    if not refresh_token:
        return JsonResponse({"error": "No refresh token"}, status=401)

    payload = decode_token(refresh_token)
    if not payload or payload.get("token_type") != "refresh":
        response = JsonResponse({"error": "Invalid or expired refresh token"}, status=401)
        clear_auth_cookies(response)
        return response

    try:
        user = User.objects.get(pk=payload["user_id"], is_active=True)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=401)

    tokens = generate_tokens(user)
    response = JsonResponse({"status": "ok"})
    set_auth_cookies(response, tokens)
    return response
