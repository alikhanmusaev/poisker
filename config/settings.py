import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


SECRET_KEY = os.getenv("SECRET_KEY", "")
_debug_env = os.getenv("DJANGO_DEBUG")
if _debug_env is not None:
    DEBUG = env_bool("DJANGO_DEBUG")
else:
    # Default secure: DEBUG off unless explicitly enabled.
    DEBUG = False

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-secret-key-unsafe"
    else:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is false.")
elif SECRET_KEY in {"dev-secret-key", "dev-secret-key-unsafe"} and not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("Refusing insecure SECRET_KEY when DEBUG is false.")
APP_DOMAIN = os.getenv("APP_DOMAIN", "poisker.ru")

_default_hosts = "localhost,127.0.0.1" if DEBUG else f"{APP_DOMAIN},www.{APP_DOMAIN}"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", _default_hosts).split(",") if h.strip()]

if DEBUG:
    _default_csrf_origins = (
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )
else:
    _default_csrf_origins = f"https://{APP_DOMAIN},https://www.{APP_DOMAIN}"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", _default_csrf_origins).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "listings",
    "messaging",
    "bookmarks",
    "moderation",
    "reviews",
    "core",
    "notifications",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.BlockedUserMiddleware",
    "core.middleware_moderator.ModeratorSellerIsolationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_context",
                "messaging.context_processors.messaging_context",
                "bookmarks.context_processors.bookmarks_context",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "chechnya_board"),
        "USER": os.getenv("POSTGRES_USER", "board"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "board"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
    }
}

_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("postgresql+psycopg://") or _db_url.startswith("postgresql://"):
    import re

    match = re.match(
        r"postgresql(?:\+psycopg)?://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<name>.+)",
        _db_url,
    )
    if match:
        DATABASES["default"].update(
            {
                "USER": match.group("user"),
                "PASSWORD": match.group("password"),
                "HOST": match.group("host"),
                "PORT": match.group("port"),
                "NAME": match.group("name"),
            }
        )

if DEBUG and os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "core:index"

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = os.getenv("TIMEZONE", "Europe/Moscow")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_FAILURE_VIEW = "core.views.csrf_failure"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("TRUST_PROXY") else None
TRUST_PROXY = env_bool("TRUST_PROXY")
SECURE_HSTS_SECONDS = 31536000 if env_bool("HSTS_ENABLED") else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("HSTS_ENABLED")
SECURE_HSTS_PRELOAD = env_bool("HSTS_ENABLED")

# --- Poisker business settings ---
HMAC_SECRET = os.getenv("HMAC_SECRET", "dev-hmac-secret")
POST_EXPIRY_DAYS = env_int("POST_EXPIRY_DAYS", 30)
DELETED_POST_RETENTION_DAYS = env_int("DELETED_POST_RETENTION_DAYS", 30)
DELETED_POST_CLEANUP_BATCH_SIZE = env_int("DELETED_POST_CLEANUP_BATCH_SIZE", 100)
REPORTS_AUTO_HIDE_THRESHOLD = env_int("REPORTS_AUTO_HIDE_THRESHOLD", 3)
CONTACT_RATE_LIMIT_PER_HOUR = env_int("CONTACT_RATE_LIMIT_PER_HOUR", 30)
AUTH_RATE_LIMIT_PER_HOUR = env_int("AUTH_RATE_LIMIT_PER_HOUR", 30)
MESSAGING_RATE_LIMIT_PER_HOUR = env_int("MESSAGING_RATE_LIMIT_PER_HOUR", 60)
REVIEW_AFTER_PHONE_HOURS = env_int("REVIEW_AFTER_PHONE_HOURS", 2)
DEAL_CONFIRM_TIMEOUT_DAYS = env_int("DEAL_CONFIRM_TIMEOUT_DAYS", 3)
REVIEW_REMINDER_DAYS = env_int("REVIEW_REMINDER_DAYS", 1)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "poisker",
        "TIMEOUT": 300,
    }
}
TYPESENSE_URL = os.getenv("TYPESENSE_URL", "http://localhost:8108")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "typesenseKey")

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "board-images")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "http://localhost:9000/board-images")

SITE_NAME = os.getenv("SITE_NAME", "Поискер")
SITE_TAGLINE = os.getenv("SITE_TAGLINE", "Доска объявлений по Чеченской Республике")
SITE_DESCRIPTION = os.getenv(
    "SITE_DESCRIPTION",
    "Поискер — бесплатные объявления по Чеченской Республике.",
)
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "info@poisker.ru")
STATIC_VERSION = os.getenv("STATIC_VERSION", "django-57")
# Version of the separate PD consent document (152-FZ / 156-FZ). Bump when text changes.
PDN_CONSENT_VERSION = os.getenv("PDN_CONSENT_VERSION", "2026-07-16b")
OPERATOR_NAME = os.getenv(
    "OPERATOR_NAME",
    "Индивидуальный предприниматель Мусаев Алихан Хизирович",
)
OPERATOR_INN = os.getenv("OPERATOR_INN", "201404274205")
OPERATOR_OGRNIP = os.getenv("OPERATOR_OGRNIP", "326200000008112")
OPERATOR_ADDRESS = os.getenv(
    "OPERATOR_ADDRESS",
    "Чеченская Республика, с. Автуры, ул. Махмуда Махаджиева, д. 2",
)

MAX_UPLOAD_SIZE = env_int("MAX_UPLOAD_SIZE", 20 * 1024 * 1024)
MAX_IMAGE_PIXELS = env_int("MAX_IMAGE_PIXELS", 20000000)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", "false")
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", "false")
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 20)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f"noreply@{APP_DOMAIN}")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
NOTIFY_SELLER_EMAIL = env_bool("NOTIFY_SELLER_EMAIL", "true")

SECURITY_HEADERS_ENABLED = env_bool("SECURITY_HEADERS_ENABLED", "true")
CONTENT_SECURITY_POLICY = os.getenv("CONTENT_SECURITY_POLICY", "")

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# --- REST API (Android) ---
from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.PoiskerPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.poisker_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Poisker API",
    "DESCRIPTION": "JSON API for Poisker mobile clients",
    "VERSION": "1.0.0",
}

# --- Firebase Cloud Messaging (server) ---
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "").strip()
FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE", "").strip()
FCM_ENABLED = env_bool("FCM_ENABLED", "true")
