"""Isolated settings for pytest; production and development still use PostgreSQL."""
from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
SECRET_KEY = "test-only-secret-key-that-is-longer-than-thirty-two-characters"
# Tests cover the production verification path. Local DEBUG development remains
# friction-free unless EMAIL_VERIFICATION_REQUIRED is explicitly enabled.
EMAIL_VERIFICATION_REQUIRED = True
