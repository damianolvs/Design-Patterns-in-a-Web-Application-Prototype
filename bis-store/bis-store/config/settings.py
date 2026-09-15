"""
Django settings for the BIS Store prototype.

Deliberately minimal:
  * DATABASES is empty -- the lab allows hardcoded data, and all state lives
    in the Singleton at store/patterns/store_state.py.
  * No sessions, no auth, no admin. Nothing here needs a database.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Prototype only. Never ship a hardcoded key in a real project.
SECRET_KEY = "django-insecure-bis-store-lab-prototype-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "store",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# No database. All state is in memory (see the Singleton).
DATABASES = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chihuahua"
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
