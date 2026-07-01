import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app.services.phone import normalize_phone


def _fernet() -> Fernet:
    secret = current_app.config["HMAC_SECRET"].encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_phone(phone: str) -> str:
    return _fernet().encrypt(normalize_phone(phone).encode()).decode()


def decrypt_phone(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None
