import os

from flask import Flask, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import config_by_name
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.utils.static_assets import compute_static_version


def _content_security_policy(app) -> str:
    return (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'"
    )


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    config_class = config_by_name.get(config_name, config_by_name["default"])
    if hasattr(config_class, "init_app"):
        config_class.init_app(app)
    app.config["STATIC_VERSION"] = compute_static_version(app.static_folder)
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
            _content_security_policy(app),
        )
        if app.config.get("HSTS_ENABLED"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        if request.args.get("token") or request.form.get("token"):
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"
        return response

    from app.routes import admin, main, media, posts, promotions, reports, search

    main.register_listing_converters(app)
    app.register_blueprint(main.bp)
    app.register_blueprint(media.bp)
    app.register_blueprint(posts.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(promotions.bp)
    app.register_blueprint(admin.bp)

    from app.utils.text_ru import plural_ru

    @app.template_filter("plural_ru")
    def plural_ru_filter(count, one, few, many):
        return plural_ru(count, one, few, many)

    from app.services.seo import listing_page_url as listing_page_url_fn

    app.jinja_env.globals["listing_page_url"] = listing_page_url_fn

    @app.context_processor
    def inject_globals():
        from datetime import timezone

        from app.constants import (
            CATEGORIES,
            CATEGORY_ICONS,
            CATEGORY_LABELS,
            CITIES,
            POST_BODY_MAX_LEN,
            POST_BODY_MIN_LEN,
            POST_TITLE_MAX_LEN,
            POST_TITLE_MIN_LEN,
            SORT_OPTIONS,
        )
        from app.models import utcnow
        from app.routes.media import resolve_image_url

        from app.utils.text_ru import plural_ru

        def relative_time(value):
            if not value:
                return ""
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            delta = utcnow() - value.astimezone(timezone.utc)
            seconds = max(int(delta.total_seconds()), 0)
            if seconds < 3600:
                minutes = max(seconds // 60, 1)
                return f"{minutes} {plural_ru(minutes, 'минуту', 'минуты', 'минут')} назад"
            if seconds < 86400:
                hours = max(seconds // 3600, 1)
                return f"{hours} {plural_ru(hours, 'час', 'часа', 'часов')} назад"
            days = seconds // 86400
            if days == 1:
                return "вчера"
            if days < 7:
                return f"{days} {plural_ru(days, 'день', 'дня', 'дней')} назад"
            return value.strftime("%d.%m.%Y")

        from app.services.seo import category_path, city_category_path, post_image_alt, post_public_url, site_description, site_name, site_tagline
        from app.utils.post_display import cover_image, ordered_images

        from app.services.captcha import (
            captcha_enabled,
            captcha_prompt,
            captcha_provider,
            captcha_site_key,
            ensure_captcha_challenge,
        )

        def static_url(filename: str) -> str:
            version = app.config.get("STATIC_VERSION", "1")
            return f"{url_for('static', filename=filename)}?v={version}"

        provider = captcha_provider()
        return {
            "static_version": app.config.get("STATIC_VERSION", "1"),
            "static_url": static_url,
            "cities": CITIES,
            "categories": CATEGORIES,
            "category_labels": CATEGORY_LABELS,
            "category_icons": CATEGORY_ICONS,
            "sort_options": SORT_OPTIONS,
            "captcha_enabled": captcha_enabled(),
            "captcha_provider": provider,
            "captcha_site_key": captcha_site_key(),
            "captcha_question": ensure_captcha_challenge() if captcha_enabled() else "",
            "captcha_prompt": captcha_prompt() if captcha_enabled() else "",
            "support_email": app.config.get("SUPPORT_EMAIL", "info@poisker.ru"),
            "app_domain": app.config.get("APP_DOMAIN", ""),
            "site_name": site_name(),
            "site_tagline": site_tagline(),
            "site_description": site_description(),
            "post_public_url": post_public_url,
            "image_url": resolve_image_url,
            "ordered_images": ordered_images,
            "cover_image": cover_image,
            "post_image_alt": post_image_alt,
            "relative_time": relative_time,
            "post_title_min_len": POST_TITLE_MIN_LEN,
            "post_title_max_len": POST_TITLE_MAX_LEN,
            "post_body_min_len": POST_BODY_MIN_LEN,
            "post_body_max_len": POST_BODY_MAX_LEN,
            "category_path": category_path,
            "city_category_path": city_category_path,
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
        if request.accept_mimetypes.best == "application/json":
            return {"error": "Слишком много запросов. Попробуйте позже."}, 429
        return render_template("errors/429.html"), 429

    from app.cli import register_cli

    register_cli(app)

    with app.app_context():
        if app.config.get("SCHEDULER_ENABLED"):
            from app.jobs.scheduler import init_scheduler

            init_scheduler(app)

    return app
