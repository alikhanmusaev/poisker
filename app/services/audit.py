from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models import AdminAuditLog
from app.services.phone import hash_value


def log_admin_action(action: str, *, target_type: str, target_id: str, ip_hash: str | None = None):
    if not current_user.is_authenticated:
        return
    entry = AdminAuditLog(
        admin_id=current_user.id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        ip_hash=ip_hash,
    )
    db.session.add(entry)
    db.session.commit()


def log_admin_action_from_request(action: str, *, target_type: str, target_id: str):
    remote = "unknown"
    try:
        from flask import request

        remote = request.remote_addr or "unknown"
    except RuntimeError:
        pass
    log_admin_action(action, target_type=target_type, target_id=target_id, ip_hash=hash_value(remote))
