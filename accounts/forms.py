"""
accounts/forms.py - Authentication forms for signup, OTP verify, and login.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

User = get_user_model()


class SignupForm(forms.Form):
    """Step 1 of registration: collect user credentials."""

    name = forms.CharField(
        max_length=150,
        label="Full Name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Ananya Sharma", "autocomplete": "name"}),
    )
    username = forms.CharField(
        max_length=150,
        label="Username",
        validators=[UnicodeUsernameValidator()],
        widget=forms.TextInput(attrs={"placeholder": "e.g. ananya2025", "autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "e.g. student@dbs.edu.in", "autocomplete": "email"}),
    )
    phone = forms.CharField(
        max_length=15,
        label="Mobile Number",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. 9876543210", "autocomplete": "tel"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Minimum 8 characters", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter your password", "autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if " " in username:
            raise ValidationError("Username cannot contain spaces. Use letters, numbers, or @/./+/-/_ only.")
        try:
            if User.objects.filter(username__iexact=username).exists():
                raise ValidationError("This username is already taken. Please choose another.")
        except ValidationError:
            raise
        except Exception:
            pass
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        try:
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("An account with this email already exists. Try logging in.")
        except ValidationError:
            raise
        except Exception:
            pass
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned


class OTPVerifyForm(forms.Form):
    """Step 2: user enters the OTP displayed on the page."""

    otp_code = forms.CharField(
        max_length=20,
        label="6-Digit OTP",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter 6-digit OTP",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "class": "otp-input",
            }
        ),
    )

    def clean_otp_code(self):
        code = self.cleaned_data["otp_code"].replace(" ", "").replace("-", "").strip()
        if len(code) != 6 or not code.isdigit():
            raise ValidationError("Please enter a valid 6-digit numeric OTP.")
        return code


class LoginForm(forms.Form):
    """Login with username (or email) and password."""

    username = forms.CharField(
        max_length=254,
        label="Username or Email",
        widget=forms.TextInput(attrs={"placeholder": "Username or email address", "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Your password", "autocomplete": "current-password"}),
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Keep me logged in for 30 days",
    )


class ForgotPasswordRequestForm(forms.Form):
    """Step 1 of forgot password: enter registered email."""

    email = forms.EmailField(
        label="Registered Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "e.g. student@dbs.edu.in", "autocomplete": "email"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError("No registered account found with this email address.")
        return email


class ResetPasswordForm(forms.Form):
    """Step 3 of forgot password: enter and re-enter new password."""

    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Minimum 8 characters", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter your new password", "autocomplete": "new-password"}),
    )

    def clean_new_password1(self):
        pw = self.cleaned_data.get("new_password1", "")
        if len(pw) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "Passwords do not match.")
        return cleaned

