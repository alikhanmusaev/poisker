import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///chechnya_board.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() not in ("0", "false", "no")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "600 per minute")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_INDEX = os.getenv("RATELIMIT_INDEX", "300 per minute")
    RATELIMIT_SUGGEST = os.getenv("RATELIMIT_SUGGEST", "180 per minute")
    TYPESENSE_URL = os.getenv("TYPESENSE_URL", "http://localhost:8108")
    TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "typesenseKey")
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET = os.getenv("S3_BUCKET", "board-images")
    S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "http://localhost:9000/board-images")
    CAPTCHA_PROVIDER = os.getenv("CAPTCHA_PROVIDER", "builtin").lower()
    CAPTCHA_TTL_SECONDS = int(os.getenv("CAPTCHA_TTL_SECONDS", "600"))
    SMARTCAPTCHA_SITE_KEY = os.getenv("SMARTCAPTCHA_SITE_KEY", "")
    SMARTCAPTCHA_SECRET_KEY = os.getenv("SMARTCAPTCHA_SECRET_KEY", "")
    HMAC_SECRET = os.getenv("HMAC_SECRET", "dev-hmac-secret")
    PHONE_ENCRYPTION_KEY = os.getenv("PHONE_ENCRYPTION_KEY", "dev-phone-encryption-key")
    POST_EXPIRY_DAYS = int(os.getenv("POST_EXPIRY_DAYS", "30"))
    POST_DAILY_LIMIT = max(int(os.getenv("POST_DAILY_LIMIT", "5")), 1)
    DELETED_POST_RETENTION_DAYS = int(os.getenv("DELETED_POST_RETENTION_DAYS", "30"))
    DELETED_POST_CLEANUP_BATCH_SIZE = int(os.getenv("DELETED_POST_CLEANUP_BATCH_SIZE", "100"))
    PROMOTIONS_ENABLED = os.getenv("PROMOTIONS_ENABLED", "false").lower() in ("1", "true", "yes")
    PROMOTION_BOOST_24H_AMOUNT = int(os.getenv("PROMOTION_BOOST_24H_AMOUNT", "100"))
    TIMEZONE = "Europe/Moscow"
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024
    MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "20000000"))
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
    CONTACT_SOFT_LIMIT = int(os.getenv("CONTACT_SOFT_LIMIT", "5"))
    CONTACT_RATE_LIMIT = os.getenv("CONTACT_RATE_LIMIT", "30 per hour")
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes")
    REQUIRE_CAPTCHA = os.getenv("REQUIRE_CAPTCHA", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    SECURITY_HEADERS_ENABLED = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() in ("1", "true", "yes")
    HSTS_ENABLED = os.getenv("HSTS_ENABLED", "false").lower() in ("1", "true", "yes")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    # Site / SEO / PWA
    APP_DOMAIN = os.getenv("APP_DOMAIN", "poisker.ru")
    SITE_NAME = os.getenv("SITE_NAME", "Поискер")
    SITE_TAGLINE = os.getenv("SITE_TAGLINE", "Доска объявлений Чеченской Республики")
    SITE_DESCRIPTION = os.getenv(
        "SITE_DESCRIPTION",
        "Поискер — бесплатные объявления по Чеченской Республике. Покупка, продажа, услуги без регистрации.",
    )
    ANDROID_PACKAGE_NAME = os.getenv("ANDROID_PACKAGE_NAME", "ru.poisker.app")
    ANDROID_SHA256_FINGERPRINTS = [
        fp.strip()
        for fp in os.getenv("ANDROID_SHA256_FINGERPRINTS", "").split(",")
        if fp.strip()
    ]
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() in ("1", "true", "yes")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "info@poisker.ru")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


class DevelopmentConfig(Config):
    DEBUG = True
    RATELIMIT_DEFAULT = "2000 per minute"
    RATELIMIT_INDEX = "600 per minute"
    RATELIMIT_SUGGEST = "300 per minute"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() in ("1", "true", "yes")
    REQUIRE_CAPTCHA = os.getenv("REQUIRE_CAPTCHA", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    HSTS_ENABLED = os.getenv("HSTS_ENABLED", "true").lower() in ("1", "true", "yes")

    @staticmethod
    def init_app(app):
        weak = []
        if app.config["SECRET_KEY"] in ("dev-secret-key", "change-me-in-production", ""):
            weak.append("SECRET_KEY")
        if app.config["HMAC_SECRET"] in ("dev-hmac-secret", "change-me-hmac-secret", ""):
            weak.append("HMAC_SECRET")
        phone_key = app.config.get("PHONE_ENCRYPTION_KEY", "")
        if phone_key in ("", "change-me-phone-encryption-key", "dev-phone-encryption-key"):
            weak.append("PHONE_ENCRYPTION_KEY")
        if phone_key and phone_key == app.config["HMAC_SECRET"]:
            raise RuntimeError("Production requires PHONE_ENCRYPTION_KEY distinct from HMAC_SECRET")
        if app.config["TYPESENSE_API_KEY"] in ("typesenseKey", "change-me-typesense-key", ""):
            weak.append("TYPESENSE_API_KEY")
        if app.config["S3_ACCESS_KEY"] in ("minioadmin", "change-me-s3-access-key", ""):
            weak.append("S3_ACCESS_KEY")
        if app.config["S3_SECRET_KEY"] in ("minioadmin", "change-me-s3-secret-key", ""):
            weak.append("S3_SECRET_KEY")
        if weak:
            app.logger.warning(
                "Production: set strong values for %s in environment variables",
                ", ".join(weak),
            )
            raise RuntimeError(f"Production requires strong values for: {', '.join(weak)}")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
