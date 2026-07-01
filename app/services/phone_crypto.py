import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

WEAK_PHONE_KEYS = {
    "",
    "change-me-phone-encryption-key",
    "dev-phone-encryption-key",
}


def _derive_fernet_key(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet_from_config_value(value: str) -> Fernet | None:
    if not value:
        return None
    try:
        return Fernet(value.encode())
    except (ValueError, TypeError):
        return _derive_fernet_key(value)


def _primary_fernet() -> Fernet:
    key = current_app.config.get("PHONE_ENCRYPTION_KEY") or ""
    fernet = _fernet_from_config_value(key)
    if fernet:
        return fernet
    return _derive_fernet_key(current_app.config["HMAC_SECRET"])


def _legacy_fernet() -> Fernet:
    return _derive_fernet_key(current_app.config["HMAC_SECRET"])


def encrypt_phone(phone: str) -> str:
    return _primary_fernet().encrypt(normalize_phone(phone).encode()).decode()


def decrypt_phone(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    for fernet in (_primary_fernet(), _legacy_fernet()):
        try:
            return fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            continue
    return None
