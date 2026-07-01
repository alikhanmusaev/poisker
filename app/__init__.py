import os

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import config_by_name
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    config_class = config_by_name.get(config_name, config_by_name["default"])
    if hasattr(config_class, "init_app"):
        config_class.init_app(app)
    app.url_map.strict_slashes = False
    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    limiter.enabled = app.config.get("RATELIMIT_ENABLED", True)
    default = app.config.get("RATELIMIT_DEFAULT")
    if default:
        limiter.default_limits = [default]

    @limiter.request_filter
    def _skip_static_rate_limit():
        return request.endpoint in ("static", "media.serve")

    @app.after_request
    def add_security_headers(response):
        if not app.config.get("SECURITY_HEADERS_ENABLED", True):
            return response
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' https://challenges.cloudflare.com; "
            "connect-src 'self' https://challenges.cloudflare.com; "
            "frame-src https://challenges.cloudflare.com; "
            "form-action 'self'",
        )
        if app.config.get("HSTS_ENABLED"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    from app.routes import admin, main, media, posts, promotions, reports, search

    app.register_blueprint(main.bp)
    app.register_blueprint(media.bp)
    app.register_blueprint(posts.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(promotions.bp)
    app.register_blueprint(admin.bp)

    @app.context_processor
    def inject_globals():
        from datetime import timezone

        from app.constants import CATEGORIES, CATEGORY_ICONS, CATEGORY_LABELS, CITIES, SORT_OPTIONS
        from app.models import utcnow
        from app.routes.media import resolve_image_url

        def relative_time(value):
            if not value:
                return ""
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            delta = utcnow() - value.astimezone(timezone.utc)
            seconds = max(int(delta.total_seconds()), 0)
            if seconds < 3600:
                minutes = max(seconds // 60, 1)
                return f"{minutes} мин назад"
            if seconds < 86400:
                hours = seconds // 3600
                return f"{hours} ч назад"
            days = seconds // 86400
            if days == 1:
                return "вчера"
            if days < 7:
                return f"{days} дн назад"
            return value.strftime("%d.%m.%Y")

        from app.services.seo import post_public_url, site_description, site_name, site_tagline

        return {
            "cities": CITIES,
            "categories": CATEGORIES,
            "category_labels": CATEGORY_LABELS,
            "category_icons": CATEGORY_ICONS,
            "sort_options": SORT_OPTIONS,
            "turnstile_site_key": app.config.get("TURNSTILE_SITE_KEY", ""),
            "support_email": app.config.get("SUPPORT_EMAIL", ""),
            "app_domain": app.config.get("APP_DOMAIN", ""),
            "site_name": site_name(),
            "site_tagline": site_tagline(),
            "site_description": site_description(),
            "post_public_url": post_public_url,
            "image_url": resolve_image_url,
            "relative_time": relative_time,
        }

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if request.headers.get("HX-Request"):
            return (
                '<p class="flash flash-error" role="alert">Слишком много запросов. Подождите минуту.</p>',
                429,
            )
        return render_template("errors/429.html"), 429

    with app.app_context():
        if app.config.get("SCHEDULER_ENABLED"):
            from app.jobs.scheduler import init_scheduler

            init_scheduler(app)

    return app
