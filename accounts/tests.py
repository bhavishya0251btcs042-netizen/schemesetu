"""
accounts/tests.py - Comprehensive tests for:
- JWT authentication
- OTP signup with EmailJS & Welcome email
- Removal of dummy OTP UI
- Forgot Password flow (Request OTP -> Verify OTP -> Reset Password)
- MongoDB integration helpers
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.jwt_utils import generate_tokens, decode_token
from accounts.models import OTPRecord
from accounts.emailjs_service import send_otp_email, send_welcome_email
from schemesetu.mongodb import get_mongo_client, sync_user_to_mongodb

User = get_user_model()


class SignupAndOTPTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup_get_renders_form(self):
        res = self.client.get(reverse("accounts:signup"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Create your account")
        self.assertContains(res, "Send OTP &amp; Continue")

    def test_signup_post_valid_creates_otp_and_shows_verify(self):
        post_data = {
            "name": "Arjun Patel",
            "username": "arjunpatel",
            "email": "arjun@example.com",
            "phone": "9876543210",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        res = self.client.post(reverse("accounts:signup"), post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Verify your email")
        self.assertContains(res, "Check your email inbox")

        # Verify OTP record created in DB
        otp = OTPRecord.objects.filter(email="arjun@example.com", is_used=False).first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)

    def test_signup_duplicate_username_fails(self):
        User.objects.create_user(username="existinguser", email="other@example.com", password="password123")
        post_data = {
            "name": "Another User",
            "username": "existinguser",
            "email": "new@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        res = self.client.post(reverse("accounts:signup"), post_data)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "This username is already taken")

    def test_signup_duplicate_email_fails(self):
        User.objects.create_user(username="user1", email="existing@example.com", password="password123")
        post_data = {
            "name": "Another User",
            "username": "user2",
            "email": "existing@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        res = self.client.post(reverse("accounts:signup"), post_data)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "An account with this email already exists")

    def test_otp_verify_correct_creates_user_and_sets_jwt(self):
        self.client.post(reverse("accounts:signup"), {
            "name": "Meera Iyer",
            "username": "meeraiyer",
            "email": "meera@example.com",
            "phone": "9998887776",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        otp = OTPRecord.objects.get(email="meera@example.com", is_used=False)

        res = self.client.post(reverse("accounts:otp_verify"), {"otp_code": otp.otp_code})
        self.assertRedirects(res, reverse("core:home"))

        user = User.objects.filter(username="meeraiyer").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "meera@example.com")
        self.assertEqual(user.first_name, "Meera")

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

        self.assertIn("access_token", res.cookies)
        self.assertIn("refresh_token", res.cookies)

    def test_otp_verify_wrong_otp_fails(self):
        self.client.post(reverse("accounts:signup"), {
            "name": "Meera Iyer",
            "username": "meeraiyer2",
            "email": "meera2@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        res = self.client.post(reverse("accounts:otp_verify"), {"otp_code": "000000"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Incorrect OTP")
        self.assertFalse(User.objects.filter(username="meeraiyer2").exists())

    def test_otp_resend_generates_fresh_otp(self):
        self.client.post(reverse("accounts:signup"), {
            "name": "Test User",
            "username": "testresend",
            "email": "resend@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        first_otp = OTPRecord.objects.get(email="resend@example.com", is_used=False)

        res = self.client.get(reverse("accounts:resend_otp"), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "A fresh OTP has been sent")

        first_otp.refresh_from_db()
        self.assertTrue(first_otp.is_used)


class ForgotPasswordFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="kavya",
            email="kavya@example.com",
            password="OldPassword123!",
            first_name="Kavya",
        )

    def test_forgot_password_page_renders(self):
        res = self.client.get(reverse("accounts:forgot_password"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Reset your password")

    def test_forgot_password_invalid_email_fails(self):
        res = self.client.post(reverse("accounts:forgot_password"), {
            "email": "notfound@example.com",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "No registered account found")

    def test_forgot_password_valid_email_sends_otp_and_redirects(self):
        res = self.client.post(reverse("accounts:forgot_password"), {
            "email": "kavya@example.com",
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Verify Reset Code")

        otp = OTPRecord.objects.filter(email="kavya@example.com", is_used=False).first()
        self.assertIsNotNone(otp)

    def test_forgot_password_verify_wrong_otp_fails(self):
        self.client.post(reverse("accounts:forgot_password"), {"email": "kavya@example.com"})
        res = self.client.post(reverse("accounts:forgot_password_verify"), {
            "otp_code": "999999",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Incorrect OTP")

    def test_forgot_password_complete_flow_updates_password(self):
        # Step 1: Request
        self.client.post(reverse("accounts:forgot_password"), {"email": "kavya@example.com"})
        otp = OTPRecord.objects.get(email="kavya@example.com", is_used=False)

        # Step 2: Verify OTP
        res_v = self.client.post(reverse("accounts:forgot_password_verify"), {"otp_code": otp.otp_code})
        self.assertRedirects(res_v, reverse("accounts:forgot_password_reset"))

        # Step 3: Set new password
        res_r = self.client.post(reverse("accounts:forgot_password_reset"), {
            "new_password1": "BrandNewPass999!",
            "new_password2": "BrandNewPass999!",
        })
        self.assertRedirects(res_r, reverse("accounts:login"))

        # Verify user can now log in with new password
        login_res = self.client.post(reverse("accounts:login"), {
            "username": "kavya",
            "password": "BrandNewPass999!",
        })
        self.assertRedirects(login_res, reverse("core:home"))


class LoginLogoutJWTTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student1",
            email="student1@dbs.edu.in",
            password="MySecretPassword123!",
            first_name="Pooja",
        )

    def test_login_get_renders_form(self):
        res = self.client.get(reverse("accounts:login"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Welcome back")
        self.assertContains(res, "Forgot password?")

    def test_login_with_username_sets_jwt_cookies(self):
        res = self.client.post(reverse("accounts:login"), {
            "username": "student1",
            "password": "MySecretPassword123!",
        })
        self.assertRedirects(res, reverse("core:home"))
        self.assertIn("access_token", res.cookies)
        self.assertIn("refresh_token", res.cookies)

    def test_logout_clears_cookies(self):
        tokens = generate_tokens(self.user)
        self.client.cookies["access_token"] = tokens["access"]
        self.client.cookies["refresh_token"] = tokens["refresh"]

        res = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(res, reverse("accounts:login"))
        self.assertEqual(res.cookies["access_token"].value, "")

    def test_profile_view_shows_user_info(self):
        tokens = generate_tokens(self.user)
        self.client.cookies["access_token"] = tokens["access"]

        res = self.client.get(reverse("accounts:profile"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "student1@dbs.edu.in")
        self.assertContains(res, "signed JWT")


class ServiceIntegrationTests(TestCase):
    def test_emailjs_fallback_dispatches_successfully(self):
        ok, msg = send_otp_email("test@example.com", "Tester", "123456", "signup")
        self.assertTrue(ok)
        ok2, msg2 = send_welcome_email("test@example.com", "Tester")
        self.assertTrue(ok2)

    @override_settings(MONGODB_URI="")
    def test_mongo_client_handles_unconfigured_gracefully(self):
        import schemesetu.mongodb as _mod
        _prev = _mod._mongo_client
        _mod._mongo_client = None  # reset cached client
        try:
            client = get_mongo_client()
            # When MONGODB_URI is empty, client is None without throwing exceptions
            self.assertIsNone(client)
            # Syncing also returns False safely without crash
            synced = sync_user_to_mongodb(User(username="test_sync"))
            self.assertFalse(synced)
        finally:
            _mod._mongo_client = _prev
