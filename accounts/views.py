"""
accounts/views.py - Authentication views:
- Signup (2-step OTP verification with EmailJS & Welcome Mail)
- Login (Username/Email + Password with JWT Cookies)
- Forgot Password (3-step: Request OTP via EmailJS -> Verify OTP -> Set New Password)
- Logout & Profile
- Silent Token Refresh
- MongoDB Dual-Sync
"""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    ForgotPasswordRequestForm,
    LoginForm,
    OTPVerifyForm,
    ResetPasswordForm,
    SignupForm,
)
from .jwt_utils import (
    clear_auth_cookies,
    decode_token,
    generate_tokens,
    set_auth_cookies,
)
from .models import OTPRecord
from .emailjs_service import (
    send_otp_email,
    send_welcome_email,
    send_password_reset_success_email,
)
from schemesetu.mongodb import (
    sync_user_to_mongodb,
    sync_otp_to_mongodb,
)

User = get_user_model()

# Session keys
_PENDING_SIGNUP_KEY = "pending_signup"
_PENDING_OTP_EMAIL_KEY = "pending_otp_email"
_PWD_RESET_EMAIL_KEY = "pwd_reset_email"
_PWD_RESET_VERIFIED_KEY = "pwd_reset_verified"


# ---------------------------------------------------------------------------
# SIGNUP — Step 1: Collect User Data & Dispatch OTP via EmailJS
# ---------------------------------------------------------------------------

def signup_view(request):
    """Collect signup data, generate OTP, send via EmailJS, redirect to verify."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            email = cd["email"]
            name = cd["name"]

            # Generate OTP (with fallback if DB table is initializing)
            otp_code = None
            try:
                OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
                otp_record = OTPRecord.objects.create(email=email)
                otp_code = otp_record.otp_code
            except Exception:
                import random
                otp_code = f"{random.randint(100000, 999999)}"

            # Mirror OTP to MongoDB (if configured)
            sync_otp_to_mongodb(email=email, otp_code=otp_code, purpose="signup")

            # Dispatch OTP email via EmailJS (or console dev fallback)
            send_otp_email(to_email=email, to_name=name, otp_code=otp_code, purpose="signup")

            # Store pending details in session
            request.session[_PENDING_SIGNUP_KEY] = {
                "name": name,
                "username": cd["username"],
                "email": email,
                "phone": cd.get("phone", ""),
                "password": cd["password1"],
            }
            request.session[_PENDING_OTP_EMAIL_KEY] = email
            request.session["pending_otp_code"] = otp_code
            request.session.modified = True

            messages.info(request, f"A 6-digit verification OTP has been sent to {email}.")
            return redirect("accounts:otp_verify")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


# ---------------------------------------------------------------------------
# SIGNUP — Step 2: Verify OTP, Create User, Send Welcome Email
# ---------------------------------------------------------------------------

def otp_verify_view(request):
    """Verify OTP, create User, dual-sync to MongoDB, send Welcome Email, set JWT."""
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
            entered_otp = form.cleaned_data["otp_code"].strip()
            session_otp = request.session.get("pending_otp_code")

            otp_record = None
            try:
                otp_record = (
                    OTPRecord.objects
                    .filter(email=email, is_used=False)
                    .order_by("-created_at")
                    .first()
                )
            except Exception:
                pass

            is_valid_otp = False
            if otp_record and not otp_record.is_expired and otp_record.otp_code == entered_otp:
                is_valid_otp = True
                try:
                    otp_record.mark_used()
                except Exception:
                    pass
            elif session_otp and session_otp == entered_otp:
                is_valid_otp = True

            if not is_valid_otp:
                messages.error(request, "Incorrect OTP. Please check the code sent to your email and try again.")
            else:
                first_name = pending["name"].split()[0] if pending["name"] else ""
                last_name = " ".join(pending["name"].split()[1:]) if " " in pending["name"] else ""

                user = None
                try:
                    user = User.objects.create_user(
                        username=pending["username"],
                        email=pending["email"],
                        password=pending["password"],
                        first_name=first_name,
                        last_name=last_name,
                    )
                except Exception:
                    try:
                        user = User.objects.filter(username=pending["username"]).first()
                    except Exception:
                        pass

                if not user:
                    messages.error(request, "Could not finalize account creation. Please try again.")
                    return render(request, "accounts/otp_verify.html", {"form": form, "email": email})

                # Sync user document to MongoDB
                sync_user_to_mongodb(user)

                # Send Welcome Email via EmailJS
                send_welcome_email(to_email=user.email, to_name=user.first_name or user.username)

                # Clean up session
                request.session.pop(_PENDING_SIGNUP_KEY, None)
                request.session.pop(_PENDING_OTP_EMAIL_KEY, None)
                request.session.pop("pending_otp_code", None)
                request.session.modified = True

                messages.success(
                    request,
                    f"Welcome to SchemeSetu, {user.first_name or user.username}! "
                    "Your account is verified and a welcome email has been sent."
                )

                tokens = generate_tokens(user)
                response = redirect("core:home")
                set_auth_cookies(response, tokens)
                return response
    else:
        # GET
        if request.GET.get("resend") == "1":
            try:
                OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
                otp_record = OTPRecord.objects.create(email=email)
                otp_code = otp_record.otp_code
            except Exception:
                import random
                otp_code = f"{random.randint(100000, 999999)}"
            request.session["pending_otp_code"] = otp_code
            request.session.modified = True
            sync_otp_to_mongodb(email=email, otp_code=otp_code, purpose="signup")
            send_otp_email(to_email=email, to_name=pending.get("name", "Student"), otp_code=otp_code, purpose="signup")
            messages.info(request, "A fresh OTP has been sent to your email.")
        form = OTPVerifyForm()

    return render(request, "accounts/otp_verify.html", {
        "form": form,
        "email": email,
    })


# ---------------------------------------------------------------------------
# OTP RESEND
# ---------------------------------------------------------------------------

def resend_otp_view(request):
    """Invalidate old OTP, create a fresh one, send via EmailJS."""
    email = request.session.get(_PENDING_OTP_EMAIL_KEY)
    pending = request.session.get(_PENDING_SIGNUP_KEY, {})
    if not email:
        messages.error(request, "Signup session expired. Please start registration again.")
        return redirect("accounts:signup")

    try:
        OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
        otp_record = OTPRecord.objects.create(email=email)
        otp_code = otp_record.otp_code
    except Exception:
        import random
        otp_code = f"{random.randint(100000, 999999)}"

    request.session["pending_otp_code"] = otp_code
    request.session.modified = True
    sync_otp_to_mongodb(email=email, otp_code=otp_code, purpose="signup")
    send_otp_email(to_email=email, to_name=pending.get("name", "Student"), otp_code=otp_code, purpose="signup")

    messages.info(request, "A fresh OTP has been sent to your email address.")
    return redirect("accounts:otp_verify")


# ---------------------------------------------------------------------------
# FORGOT PASSWORD — Step 1: Enter Email & Request OTP
# ---------------------------------------------------------------------------

def forgot_password_request_view(request):
    """User enters registered email. Check if exists, generate OTP, send via EmailJS."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = ForgotPasswordRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.get(email__iexact=email)

            # Invalidate previous OTPs
            OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)

            # Create fresh OTP
            otp_record = OTPRecord.objects.create(email=email)
            sync_otp_to_mongodb(email=email, otp_code=otp_record.otp_code, purpose="password_reset")

            # Dispatch OTP email via EmailJS
            send_otp_email(
                to_email=email,
                to_name=user.first_name or user.username,
                otp_code=otp_record.otp_code,
                purpose="password_reset",
            )

            # Store in session
            request.session[_PWD_RESET_EMAIL_KEY] = email
            request.session[_PWD_RESET_VERIFIED_KEY] = False
            request.session.modified = True

            messages.info(request, f"Password reset OTP sent to {email}.")
            return redirect("accounts:forgot_password_verify")
    else:
        form = ForgotPasswordRequestForm()

    return render(request, "accounts/forgot_password_request.html", {"form": form})


# ---------------------------------------------------------------------------
# FORGOT PASSWORD — Step 2: Verify Password Reset OTP
# ---------------------------------------------------------------------------

def forgot_password_verify_view(request):
    """Verify the OTP sent for password reset."""
    if request.user.is_authenticated:
        return redirect("core:home")

    email = request.session.get(_PWD_RESET_EMAIL_KEY)
    if not email:
        messages.error(request, "Password reset session expired. Please enter your email again.")
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data["otp_code"]

            otp_record = (
                OTPRecord.objects
                .filter(email=email, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if otp_record is None:
                messages.error(request, "No active OTP found. Please request a new one.")
            elif otp_record.is_expired:
                messages.error(request, "OTP has expired. Please request a new one.")
                otp_record.mark_used()
            elif otp_record.otp_code != entered_otp:
                messages.error(request, "Incorrect OTP. Please check your email and try again.")
            else:
                otp_record.mark_used()
                request.session[_PWD_RESET_VERIFIED_KEY] = True
                request.session.modified = True
                messages.success(request, "OTP verified! Now enter your new password.")
                return redirect("accounts:forgot_password_reset")
    else:
        if request.GET.get("resend") == "1":
            user = User.objects.filter(email__iexact=email).first()
            name = (user.first_name or user.username) if user else "User"
            OTPRecord.objects.filter(email=email, is_used=False).update(is_used=True)
            otp_record = OTPRecord.objects.create(email=email)
            sync_otp_to_mongodb(email=email, otp_code=otp_record.otp_code, purpose="password_reset")
            send_otp_email(to_email=email, to_name=name, otp_code=otp_record.otp_code, purpose="password_reset")
            messages.info(request, "A new password reset OTP has been sent to your email.")
        form = OTPVerifyForm()

    return render(request, "accounts/forgot_password_verify.html", {
        "form": form,
        "email": email,
    })


# ---------------------------------------------------------------------------
# FORGOT PASSWORD — Step 3: Enter & Confirm New Password
# ---------------------------------------------------------------------------

def forgot_password_reset_view(request):
    """User enters and confirms new password. Updates password in DB."""
    if request.user.is_authenticated:
        return redirect("core:home")

    email = request.session.get(_PWD_RESET_EMAIL_KEY)
    verified = request.session.get(_PWD_RESET_VERIFIED_KEY)

    if not email or not verified:
        messages.error(request, "Please verify your OTP before resetting password.")
        return redirect("accounts:forgot_password")

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "Account not found. Please start again.")
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_pw = form.cleaned_data["new_password1"]
            user.set_password(new_pw)
            user.save()

            # Mirror to MongoDB
            sync_user_to_mongodb(user)

            # Send confirmation email via EmailJS
            send_password_reset_success_email(to_email=user.email, to_name=user.first_name or user.username)

            # Clean session
            request.session.pop(_PWD_RESET_EMAIL_KEY, None)
            request.session.pop(_PWD_RESET_VERIFIED_KEY, None)
            request.session.modified = True

            messages.success(request, "Your password has been successfully reset! Please log in.")
            return redirect("accounts:login")
    else:
        form = ResetPasswordForm()

    return render(request, "accounts/forgot_password_reset.html", {
        "form": form,
        "email": email,
    })


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

            user = authenticate(request, username=identifier, password=password)
            if user is None:
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
# SILENT TOKEN REFRESH
# ---------------------------------------------------------------------------

def token_refresh_view(request):
    """Silently refresh the access token using the refresh cookie."""
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
