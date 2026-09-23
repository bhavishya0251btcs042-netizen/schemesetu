import os
import logging
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "schemesetu.settings")

application = get_wsgi_application()
app = application

# Run DB migration and bootstrap automatically on serverless boot
def _auto_init():
    try:
        from django.core.management import call_command
        call_command("migrate", interactive=False)
        try:
            call_command("bootstrap")
        except Exception as e:
            logging.warning(f"Auto bootstrap notice: {e}")
    except Exception as e:
        logging.warning(f"Auto migration notice: {e}")

try:
    _auto_init()
except Exception:
    pass
