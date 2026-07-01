import hashlib
import hmac
import re
import secrets

from flask import current_app


PHONE_RE = re.compile(r"^\+7\d{10}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+7{digits}"
    raise ValueError("Введите корректный мобильный номер +7")


def validate_phone(raw: str) -> str:
    phone = normalize_phone(raw)
    if not PHONE_RE.match(phone):
        raise ValueError("Введите корректный мобильный номер +7")
    return phone


def hash_value(value: str) -> str:
    secret = current_app.config["HMAC_SECRET"].encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def hash_phone(phone: str) -> str:
    return hash_value(normalize_phone(phone))


def mask_phone(phone: str) -> str:
    p = normalize_phone(phone)
    return f"+7 *** *** {p[-5:-2]}-{p[-2:]}"


def generate_edit_token() -> str:
    return secrets.token_urlsafe(32)
