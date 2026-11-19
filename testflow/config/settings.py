import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [item.strip() for item in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "corsheaders", "rest_framework", "django_filters", "drf_spectacular",
    "apps.security", "apps.accounts", "apps.projects", "apps.requirements", "apps.test_cases", "apps.executions", "apps.defects", "apps.reports", "apps.analytics", "apps.audit", "apps.ai_assistant", "apps.demo_api",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "apps.security.middleware.SessionPolicyMiddleware", "apps.security.middleware.SecurityHeadersMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": dj_database_url.config(default=os.getenv("DATABASE_URL", "postgresql://testflow:testflow@localhost:5432/testflow"), conn_max_age=600)}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
CORS_ALLOWED_ORIGINS = [item.strip() for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("apps.security.permissions.VerifiedUser",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend", "rest_framework.filters.SearchFilter", "rest_framework.filters.OrderingFilter"),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.api_exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"ai": "20/hour"},
}

# Integrated security uses the existing User and database; no parallel identities.
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL','http://localhost:5173').rstrip('/')
# The public backend address is deliberately separate from the React address:
# a GitHub Actions runner calls Django directly, not the browser client.
PUBLIC_API_URL = os.getenv('PUBLIC_API_URL', 'http://127.0.0.1:8000').rstrip('/')
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', '')
CSRF_TRUSTED_ORIGINS = [PUBLIC_BASE_URL] + (['http://localhost:5173','http://127.0.0.1:5173'] if DEBUG else [])
TRUSTED_PROXY_IPS = [x.strip() for x in os.getenv('TRUSTED_PROXY_IPS','').split(',') if x.strip()]
TOTP_ENCRYPTION_KEY = os.environ['TOTP_ENCRYPTION_KEY']
Fernet(TOTP_ENCRYPTION_KEY.encode())
TURNSTILE_TEST_MODE = os.getenv('TURNSTILE_TEST_MODE','false').lower() == 'true'
TURNSTILE_SITE_KEY = os.environ['TURNSTILE_SITE_KEY']
TURNSTILE_SECRET_KEY = os.environ['TURNSTILE_SECRET_KEY']
TURNSTILE_ALLOWED_HOSTNAMES = os.getenv('TURNSTILE_ALLOWED_HOSTNAMES','localhost,127.0.0.1').split(',')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID','')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET','')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST','127.0.0.1')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','11025'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS','false').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_TIMEOUT = 10
EMAIL_VERIFICATION_REQUIRED = os.getenv('EMAIL_VERIFICATION_REQUIRED', 'true' if not DEBUG else 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','WebTestCase <noreply@wtc.local>')
PASSWORD_HASHERS = ['django.contrib.auth.hashers.Argon2PasswordHasher','django.contrib.auth.hashers.PBKDF2PasswordHasher']
AUTH_PASSWORD_VALIDATORS = [{'NAME':'apps.security.validators.PasswordPolicy'}]
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'apps.security.api.exception_handler'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT',str(not DEBUG)).lower() == 'true'
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCK_SECONDS = 900
OTP_FAILURE_LIMIT = 5
CHALLENGE_SECONDS = 300
if not DEBUG:
    if TURNSTILE_TEST_MODE or TURNSTILE_SITE_KEY.startswith(('1x000','2x000','3x000')) or TURNSTILE_SECRET_KEY.startswith(('1x000','2x000','3x000')):
        raise ImproperlyConfigured('У production потрібні справжні ключі Turnstile.')
    if len(SECRET_KEY)<40 or SECRET_KEY.startswith('development-') or not PUBLIC_BASE_URL.startswith('https://'):
        raise ImproperlyConfigured('Production потребує випадкового SECRET_KEY та HTTPS.')
