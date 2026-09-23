"""Automated Student Notification Engine.

Evaluates newly ingested scholarships against registered student profiles
and dispatches personalized alerts via email and in-app notifications.
"""
import logging
from typing import Dict, List, Tuple

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from core.eligibility import evaluate
from core.models import NotificationLog, Scheme, StudentSubscriber

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches notifications to eligible student subscribers for new schemes."""

    @staticmethod
    def notify_subscribers_for_scheme(scheme: Scheme) -> List[NotificationLog]:
        """
        Evaluate all active student subscribers against a scheme and dispatch notifications to eligible ones.
        Returns a list of created NotificationLog instances.
        """
        created_logs = []
        active_subscribers = StudentSubscriber.objects.filter(is_active=True)

        for subscriber in active_subscribers:
            # Prevent duplicate alerts
            if NotificationLog.objects.filter(subscriber=subscriber, scheme=scheme).exists():
                continue

            profile = subscriber.as_profile()
            is_eligible, reasons = evaluate(scheme, profile)

            if is_eligible:
                pass_reasons = [text for status, text in reasons if status == "pass"]
                matched_summary = "\n".join(f"• {r}" for r in pass_reasons)

                subject = f"🎯 New Scholarship Alert: You qualify for {scheme.name}!"
                message = (
                    f"Dear {subscriber.name},\n\n"
                    f"SchemeSetu has automatically detected a new scholarship that matches your student profile!\n\n"
                    f"Scholarship: {scheme.name}\n"
                    f"Department: {scheme.department or 'Government of India'}\n\n"
                    f"Why you qualify:\n{matched_summary}\n\n"
                    f"Benefits:\n{scheme.benefits}\n\n"
                    f"Apply directly in SchemeSetu without leaving the product:\n"
                    f"http://127.0.0.1:8000/scheme/{scheme.pk}/apply/\n\n"
                    f"Best regards,\n"
                    f"SchemeSetu Automated Citizen Services Navigator\n"
                    f"Powered by DAC · DBS Global University R&D and S&I Cell\n"
                )

                # Send email via configured backend (console/file/smtp)
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            "SchemeSetu Alerts <alerts@schemesetu.dac.gov.in>",
                        ),
                        recipient_list=[subscriber.email],
                        fail_silently=True,
                    )
                    status = "sent"
                except Exception as e:
                    logger.error(f"Failed to send email to {subscriber.email}: {e}")
                    status = "failed"

                log = NotificationLog.objects.create(
                    subscriber=subscriber,
                    scheme=scheme,
                    channel="email",
                    status=status,
                    subject=subject,
                    message=message,
                    matched_reasons=matched_summary,
                )
                created_logs.append(log)

        return created_logs

    @classmethod
    def notify_for_multiple_schemes(cls, schemes: List[Scheme]) -> Dict[str, int]:
        """Process a list of schemes and notify eligible students."""
        total_notifications = 0
        schemes_processed = 0

        for scheme in schemes:
            logs = cls.notify_subscribers_for_scheme(scheme)
            total_notifications += len(logs)
            schemes_processed += 1

        return {
            "schemes_processed": schemes_processed,
            "notifications_dispatched": total_notifications,
        }
