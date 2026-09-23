"""
accounts/models.py - OTPRecord stores a pending OTP during the signup flow.
The record is tied to the user email (before User object exists) and
expires after 10 minutes. Consumed once (is_used=True) on successful verify.
"""
import random
import string
from datetime import timedelta

from django.db import models
from django.utils import timezone


def _generate_otp():
    """Return a cryptographically-random 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


class OTPRecord(models.Model):
    """Stores a pending one-time-password for email verification at signup."""

    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6, default=_generate_otp)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OTP Record"
        verbose_name_plural = "OTP Records"

    def __str__(self):
        return f"OTP for {self.email} ({'used' if self.is_used else 'pending'})"

    @property
    def is_expired(self):
        """OTP is valid for 10 minutes."""
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])
