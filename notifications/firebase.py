"""Firebase Admin SDK bootstrap for FCM."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_initialized = False


def firebase_ready() -> bool:
    ensure_firebase_app()
    return _initialized


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes", "on")


def ensure_firebase_app() -> bool:
    """Initialize Firebase Admin once. Returns True if ready to send."""
    global _initialized
    if _initialized:
        return True

    if not getattr(settings, "FCM_ENABLED", True):
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("firebase-admin is not installed; push disabled")
        return False

    if firebase_admin._apps:
        _initialized = True
        return True

    project_id = (getattr(settings, "FIREBASE_PROJECT_ID", "") or "").strip()
    cred_file = (getattr(settings, "FIREBASE_CREDENTIALS_FILE", "") or "").strip()
    use_adc = _env_flag("FCM_USE_ADC") or bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

    if not cred_file and not use_adc:
        logger.info("Firebase credentials not configured; push disabled")
        return False

    try:
        if cred_file:
            path = Path(cred_file)
            if not path.is_file():
                logger.error("FIREBASE_CREDENTIALS_FILE not found")
                return False
            cred = credentials.Certificate(str(path))
            options = {"projectId": project_id} if project_id else None
            firebase_admin.initialize_app(cred, options)
        else:
            firebase_admin.initialize_app(
                options={"projectId": project_id} if project_id else None,
            )
        _initialized = True
        return True
    except Exception:
        logger.exception("Firebase Admin init failed")
        return False
