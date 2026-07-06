from urllib.parse import urlparse

from flask import current_app, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from wtforms import ValidationError

from flask_wtf.csrf import validate_csrf


def get_client_ip() -> str:
    if current_app.config.get("TRUST_PROXY"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address()


def contact_rate_key() -> str:
    return f"contact:{get_client_ip()}"


def contact_post_rate_key() -> str:
    post_id = request.view_args.get("post_id", "") if request.view_args else ""
    return f"contact-post:{post_id}:{get_client_ip()}"


def _allowed_csrf_referrer_hosts() -> set[str]:
    host = (request.host or "").split(":")[0].lower()
    domain = (current_app.config.get("APP_DOMAIN") or host).lower()
    hosts = {host, domain, f"www.{domain}"}
    if domain.startswith("www."):
        hosts.add(domain.removeprefix("www."))
    return hosts


def _csrf_referrer_allowed() -> bool:
    ref = (request.referrer or "").strip()
    if not ref or ref.lower() in {"null", "about:blank"}:
        # CSRF token already validated; mobile/in-app browsers may send literal "null".
        return True
    ref_host = urlparse(ref).netloc.split(":")[0].lower()
    if not ref_host:
        return True
    return ref_host in _allowed_csrf_referrer_hosts()


class PoiskerCSRFProtect(CSRFProtect):
    def protect(self):
        if request.method not in current_app.config["WTF_CSRF_METHODS"]:
            return

        try:
            validate_csrf(self._get_csrf_token())
        except ValidationError as e:
            self._error_response(e.args[0])

        if request.is_secure and current_app.config.get("WTF_CSRF_SSL_STRICT", True):
            if not _csrf_referrer_allowed():
                self._error_response("The referrer does not match the host.")

        from flask import g

        g.csrf_valid = True


db = SQLAlchemy()
migrate = Migrate()
csrf = PoiskerCSRFProtect()
limiter = Limiter(key_func=get_client_ip, default_limits=[])
login_manager = LoginManager()
login_manager.login_view = "admin.login"
