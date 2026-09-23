import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Dev key — for a campus pilot only. Regenerate before any public deployment.
SECRET_KEY = os.getenv("SECRET_KEY", "dac-schemesetu-dev-key-change-me-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.JWTAuthMiddleware",          # JWT cookie authentication (sets request.user from JWT)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "schemesetu.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "schemesetu.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Product branding (DAC guideline: unique identity + DAC association)
PRODUCT_NAME = "SchemeSetu"
PRODUCT_TAGLINE = "AI Citizen Services Navigator"
DAC_FOOTER = "Powered by DAC \u00b7 DBS Global University R&D and S&I Cell"

# Outbound Notification Gateway (console backend for safe offline logs / pluggable SMTP)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "SchemeSetu Alerts <alerts@schemesetu.dac.gov.in>"

# ---------------------------------------------------------------------------
# JWT Authentication Settings
# ---------------------------------------------------------------------------
# Uses the project SECRET_KEY by default; override JWT_SECRET in production.
JWT_ACCESS_EXPIRY_MINUTES = 15   # short-lived access token
JWT_REFRESH_EXPIRY_DAYS = 7      # refresh token valid for 7 days (30 if remember_me)

# Where @login_required redirects unauthenticated users
LOGIN_URL = "/auth/login/"

# ---------------------------------------------------------------------------
# MongoDB Database Configuration (.env driven)
# ---------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "schemesetu").strip()

# ---------------------------------------------------------------------------
# EmailJS Gateway Configuration (.env driven)
# ---------------------------------------------------------------------------
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "").strip()
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "").strip()
EMAILJS_WELCOME_TEMPLATE_ID = os.getenv("EMAILJS_WELCOME_TEMPLATE_ID", "").strip()
EMAILJS_PUBLIC_KEY = os.getenv("EMAILJS_PUBLIC_KEY", "").strip()
EMAILJS_PRIVATE_KEY = os.getenv("EMAILJS_PRIVATE_KEY", "").strip()

# ---------------------------------------------------------------------------
# Base Website URL (Used for links in emails and deployment)
# ---------------------------------------------------------------------------
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")

