"""
accounts/tests.py - Comprehensive tests for JWT authentication and OTP signup flow.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.jwt_utils import generate_tokens, decode_token
from accounts.models import OTPRecord

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
        self.assertContains(res, "Demo OTP (visible for testing)")

        # Verify OTP record created in DB
        otp = OTPRecord.objects.filter(email="arjun@example.com", is_used=False).first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertContains(res, otp.otp_code)

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
        # Step 1: initiate signup
        self.client.post(reverse("accounts:signup"), {
            "name": "Meera Iyer",
            "username": "meeraiyer",
            "email": "meera@example.com",
            "phone": "9998887776",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        otp = OTPRecord.objects.get(email="meera@example.com", is_used=False)

        # Step 2: submit correct OTP
        res = self.client.post(reverse("accounts:otp_verify"), {"otp_code": otp.otp_code})
        self.assertRedirects(res, reverse("core:home"))

        # User created in DB
        user = User.objects.filter(username="meeraiyer").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "meera@example.com")
        self.assertEqual(user.first_name, "Meera")
        self.assertEqual(user.last_name, "Iyer")

        # OTP marked as used
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

        # JWT cookies set on response
        self.assertIn("access_token", res.cookies)
        self.assertIn("refresh_token", res.cookies)
        access_payload = decode_token(res.cookies["access_token"].value)
        self.assertIsNotNone(access_payload)
        self.assertEqual(access_payload["username"], "meeraiyer")

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

    def test_otp_verify_expired_otp_fails(self):
        self.client.post(reverse("accounts:signup"), {
            "name": "Meera Iyer",
            "username": "meeraiyer3",
            "email": "meera3@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        otp = OTPRecord.objects.get(email="meera3@example.com", is_used=False)
        # Artificially age the OTP by 11 minutes
        otp.created_at = timezone.now() - timedelta(minutes=11)
        otp.save()

        res = self.client.post(reverse("accounts:otp_verify"), {"otp_code": otp.otp_code})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "OTP has expired")
        self.assertFalse(User.objects.filter(username="meeraiyer3").exists())

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
        self.assertContains(res, "A new OTP has been generated")

        first_otp.refresh_from_db()
        self.assertTrue(first_otp.is_used)

        second_otp = OTPRecord.objects.filter(email="resend@example.com", is_used=False).first()
        self.assertIsNotNone(second_otp)


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
        self.assertContains(res, "Secured with JWT")

    def test_login_with_username_sets_jwt_cookies(self):
        res = self.client.post(reverse("accounts:login"), {
            "username": "student1",
            "password": "MySecretPassword123!",
        })
        self.assertRedirects(res, reverse("core:home"))
        self.assertIn("access_token", res.cookies)
        self.assertIn("refresh_token", res.cookies)

        access_payload = decode_token(res.cookies["access_token"].value)
        self.assertEqual(access_payload["username"], "student1")
        self.assertEqual(access_payload["email"], "student1@dbs.edu.in")

    def test_login_with_email_sets_jwt_cookies(self):
        res = self.client.post(reverse("accounts:login"), {
            "username": "student1@dbs.edu.in",
            "password": "MySecretPassword123!",
        })
        self.assertRedirects(res, reverse("core:home"))
        self.assertIn("access_token", res.cookies)
        access_payload = decode_token(res.cookies["access_token"].value)
        self.assertEqual(access_payload["username"], "student1")

    def test_login_invalid_password_fails(self):
        res = self.client.post(reverse("accounts:login"), {
            "username": "student1",
            "password": "WrongPassword!",
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Invalid username/email or password")
        self.assertNotIn("access_token", res.cookies)

    def test_logout_clears_cookies(self):
        tokens = generate_tokens(self.user)
        self.client.cookies["access_token"] = tokens["access"]
        self.client.cookies["refresh_token"] = tokens["refresh"]

        res = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(res, reverse("accounts:login"))
        # Verify cookies deleted (empty or max-age 0)
        self.assertEqual(res.cookies["access_token"].value, "")
        self.assertEqual(res.cookies["refresh_token"].value, "")

    def test_jwt_middleware_authenticates_protected_views(self):
        tokens = generate_tokens(self.user)
        self.client.cookies["access_token"] = tokens["access"]

        # /check/ is protected by @login_required
        res = self.client.get(reverse("core:check"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Pooja")  # User greeting in nav

    def test_unauthenticated_redirected_to_login(self):
        self.client.cookies.clear()
        res = self.client.get(reverse("core:check"))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse("accounts:login"), res.url)

    def test_profile_view_shows_user_info(self):
        tokens = generate_tokens(self.user)
        self.client.cookies["access_token"] = tokens["access"]

        res = self.client.get(reverse("accounts:profile"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "student1@dbs.edu.in")
        self.assertContains(res, "Pooja")
        self.assertContains(res, "signed JWT")
