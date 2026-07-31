"""T-Bank (Tinkoff) Acquiring API v2 — Init + notification token helpers."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TBankError(Exception):
    def __init__(self, message: str, *, code: str | None = None, payload: dict | None = None):
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


def _password() -> str:
    return (getattr(settings, "TBANK_PASSWORD", "") or "").strip()


def _terminal_key() -> str:
    return (getattr(settings, "TBANK_TERMINAL_KEY", "") or "").strip()


def _api_url() -> str:
    return (
        getattr(settings, "TBANK_API_URL", "") or "https://securepay.tinkoff.ru/v2"
    ).rstrip("/")


def is_configured() -> bool:
    return bool(_terminal_key() and _password())


def generate_token(payload: dict[str, Any], password: str | None = None) -> str:
    """SHA-256 of concatenated Password + sorted root-level scalar fields."""
    pwd = password if password is not None else _password()
    data: dict[str, Any] = {
        k: v
        for k, v in payload.items()
        if k != "Token" and not isinstance(v, (dict, list)) and v is not None
    }
    data["Password"] = pwd
    concatenated = "".join(str(data[key]) for key in sorted(data.keys()))
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()


def verify_notification(payload: dict[str, Any]) -> bool:
    received = str(payload.get("Token") or "")
    if not received:
        return False
    expected = generate_token(payload)
    return hmac.compare_digest(expected.lower(), received.lower())


def init_payment(
    *,
    amount_kopecks: int,
    order_id: str,
    description: str,
    notification_url: str,
    success_url: str,
    fail_url: str,
    customer_email: str | None = None,
) -> dict[str, Any]:
    if not is_configured():
        raise TBankError("T-Bank is not configured (TBANK_TERMINAL_KEY / TBANK_PASSWORD).")

    body: dict[str, Any] = {
        "TerminalKey": _terminal_key(),
        "Amount": int(amount_kopecks),
        "OrderId": str(order_id),
        "Description": (description or "")[:250],
        "NotificationURL": notification_url,
        "SuccessURL": success_url,
        "FailURL": fail_url,
        "Language": "ru",
        "PayType": "O",
    }
    if customer_email:
        body["DATA"] = {"Email": customer_email}
    body["Token"] = generate_token(body)

    url = f"{_api_url()}/Init"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=body)
            data = response.json()
    except Exception as exc:
        logger.exception("T-Bank Init request failed")
        raise TBankError(f"T-Bank Init request failed: {exc}") from exc

    if not data.get("Success"):
        raise TBankError(
            data.get("Message") or data.get("Details") or "T-Bank Init failed",
            code=str(data.get("ErrorCode") or ""),
            payload=data,
        )
    if not data.get("PaymentURL"):
        raise TBankError("T-Bank Init returned no PaymentURL", payload=data)
    return data
