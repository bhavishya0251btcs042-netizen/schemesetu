"""Automated scholarship sync & proactive student alert command.

Usage:
  python manage.py sync_scholarships
  python manage.py sync_scholarships --notify
  python manage.py sync_scholarships --daemon --interval 3600
"""
import time
from django.core.management.base import BaseCommand

from core.models import Scheme, StudentSubscriber
from core.services.fetcher import ScholarshipFetcher
from core.services.notifier import NotificationDispatcher


class Command(BaseCommand):
    help = "Fetch newly announced scholarships from external platforms and proactively notify eligible students."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default=None,
            help="Optional external portal JSON/REST feed URL.",
        )
        parser.add_argument(
            "--no-notify",
            action="store_true",
            help="Sync schemes only without dispatching student notifications.",
        )
        parser.add_argument(
            "--notify-all",
            action="store_true",
            help="Evaluate and notify across all existing schemes in database.",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Run continuously in background daemon mode.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=300,
            help="Polling interval in seconds when in daemon mode (default 300s).",
        )

    def handle(self, *args, **options):
        url = options.get("url")
        should_notify = not options.get("no_notify")
        notify_all = options.get("notify_all")
        is_daemon = options.get("daemon")
        interval = options.get("interval")

        self.stdout.write(
            self.style.NOTICE(
                "===============================================================\n"
                " SchemeSetu Automated Scholarship Ingestion & Alert Engine\n"
                " Powered by DAC · DBS Global University R&D and S&I Cell\n"
                "==============================================================="
            )
        )

        def run_sync_cycle():
            fetcher = ScholarshipFetcher(source_url=url)
            self.stdout.write("[Sync] Fetching new opportunities from external portals...")
            new_schemes, updated_schemes = fetcher.sync_to_database()

            self.stdout.write(
                self.style.SUCCESS(
                    f"[Sync] Ingestion completed: {len(new_schemes)} new scholarships added, "
                    f"{len(updated_schemes)} updated. Total active: {Scheme.objects.count()}."
                )
            )

            if should_notify:
                schemes_to_eval = (
                    list(Scheme.objects.all()) if notify_all else new_schemes
                )
                subscribers_count = StudentSubscriber.objects.filter(is_active=True).count()
                self.stdout.write(
                    f"[Alerts] Evaluating {len(schemes_to_eval)} schemes against {subscribers_count} active student subscribers..."
                )

                res = NotificationDispatcher.notify_for_multiple_schemes(schemes_to_eval)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[Alerts] Dispatched {res['notifications_dispatched']} personalized student alerts successfully!"
                    )
                )

        if is_daemon:
            self.stdout.write(
                self.style.WARNING(f"Running in daemon mode. Polling every {interval} seconds. Press Ctrl+C to stop.")
            )
            while True:
                try:
                    run_sync_cycle()
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.stdout.write("Stopping daemon.")
                    break
        else:
            run_sync_cycle()
