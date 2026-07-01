from flask import current_app, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


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


db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_client_ip, default_limits=[])
login_manager = LoginManager()
login_manager.login_view = "admin.login"
