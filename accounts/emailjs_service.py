"""
accounts/emailjs_service.py — EmailJS service dispatcher for sending OTPs,
Welcome Emails, and Password Reset notifications via EmailJS REST API.

If EmailJS credentials are not set in .env, it gracefully logs the message to
console and terminal for offline development / testing.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"


def send_emailjs_email(to_email, to_name, subject, message_body, template_params_extra=None, template_id=None):
    """
    Dispatch an email via EmailJS REST API.
    Returns (success: bool, info: str).
    """
    service_id = getattr(settings, "EMAILJS_SERVICE_ID", "")
    template_id = template_id or getattr(settings, "EMAILJS_TEMPLATE_ID", "")
    public_key = getattr(settings, "EMAILJS_PUBLIC_KEY", "")
    private_key = getattr(settings, "EMAILJS_PRIVATE_KEY", "")

    site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    template_params = {
        "to_email": to_email,
        "to_name": to_name or "Student",
        "subject": subject,
        "message": message_body,
        "app_name": "SchemeSetu",
        "site_url": site_url,
    }
    if template_params_extra:
        template_params.update(template_params_extra)

    # Check if configured
    if service_id and template_id and public_key:
        payload = {
            "service_id": service_id,
            "template_id": template_id,
            "user_id": public_key,
            "template_params": template_params,
        }
        if private_key:
            payload["accessToken"] = private_key

        try:
            headers = {
                "Content-Type": "application/json",
                "Origin": getattr(settings, "SITE_URL", "http://localhost"),
                "User-Agent": "Mozilla/5.0 (compatible; SchemeSetu/1.0)",
            }
            resp = requests.post(EMAILJS_API_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                logger.info(f"EmailJS email sent to {to_email}: {subject}")
                return True, "Email sent via EmailJS"
            else:
                logger.warning(f"EmailJS responded with status {resp.status_code}: {resp.text}")
                return False, f"EmailJS status {resp.status_code}"
        except Exception as e:
            logger.error(f"EmailJS request error: {e}")
            return False, str(e)
    else:
        # Development / offline fallback
        print("\n" + "=" * 60)
        print(f"[EMAIL DISPATCH via EmailJS Gateway (Dev Fallback)]")
        print(f"To:      {to_name} <{to_email}>")
        print(f"Subject: {subject}")
        print("-" * 60)
        print(message_body)
        print("=" * 60 + "\n")
        return True, "Email logged to console (EmailJS keys not configured in .env)"


def send_otp_email(to_email, to_name, otp_code, purpose="signup"):
    """Send an OTP code for signup or password reset."""
    if purpose == "password_reset":
        subject = f"Your SchemeSetu Password Reset OTP: {otp_code}"
        body = (
            f"Hello {to_name},\n\n"
            f"You requested to reset your password for SchemeSetu.\n"
            f"Your 6-digit verification code is: {otp_code}\n\n"
            f"This code will expire in 10 minutes. If you did not request this, please ignore this email.\n\n"
            f"-- SchemeSetu Team"
        )
    else:
        subject = f"Your SchemeSetu Verification OTP: {otp_code}"
        body = (
            f"Hello {to_name},\n\n"
            f"Thank you for signing up on SchemeSetu - AI Citizen Services Navigator.\n"
            f"Your 6-digit email verification OTP is: {otp_code}\n\n"
            f"Enter this OTP on the verification page to activate your account.\n"
            f"This code will expire in 10 minutes.\n\n"
            f"-- SchemeSetu Team"
        )
    return send_emailjs_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        message_body=body,
        template_params_extra={"otp_code": otp_code, "purpose": purpose},
    )


def send_welcome_email(to_email, to_name):
    """Send a welcome email after successful signup verification."""
    subject = "Welcome to SchemeSetu! Your Account is Active"
    body = (
        f"Hello {to_name},\n\n"
        f"Welcome to SchemeSetu - AI Citizen Services Navigator!\n\n"
        f"Your account is now verified and active. You can now:\n"
        f"1. Check your eligibility across dozens of state & national scholarships.\n"
        f"2. Apply directly within the app.\n"
        f"3. Receive automated alerts whenever a matching scholarship opens.\n\n"
        f"Visit your dashboard: {getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/\n\n"
        f"Best regards,\n"
        f"SchemeSetu - Powered by DAC"
    )
    welcome_tpl_id = getattr(settings, "EMAILJS_WELCOME_TEMPLATE_ID", "") or getattr(settings, "EMAILJS_TEMPLATE_ID", "")
    return send_emailjs_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        message_body=body,
        template_params_extra={"welcome": True},
        template_id=welcome_tpl_id,
    )


def send_password_reset_success_email(to_email, to_name):
    """Send confirmation that password has been changed."""
    subject = "Your SchemeSetu Password Has Been Updated"
    body = (
        f"Hello {to_name},\n\n"
        f"This is a confirmation that your password for SchemeSetu was successfully changed.\n\n"
        f"If you did not perform this change, please contact support immediately.\n\n"
        f"-- SchemeSetu Team"
    )
    return send_emailjs_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        message_body=body,
    )

