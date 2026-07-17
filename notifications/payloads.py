"""Push payload types and URL sanitization."""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

TYPE_MESSAGE = "message"
TYPE_LISTING_APPROVED = "listing_approved"
TYPE_LISTING_REJECTED = "listing_rejected"
TYPE_LISTING_EXPIRING = "listing_expiring"
TYPE_LISTING_EXPIRED = "listing_expired"
TYPE_SYSTEM = "system"
TYPE_MARKETING = "marketing"

SUPPORTED_TYPES = frozenset(
    {
        TYPE_MESSAGE,
        TYPE_LISTING_APPROVED,
        TYPE_LISTING_REJECTED,
        TYPE_LISTING_EXPIRING,
        TYPE_LISTING_EXPIRED,
        TYPE_SYSTEM,
        TYPE_MARKETING,
    }
)

LISTING_KINDS = frozenset(
    {
        TYPE_LISTING_APPROVED,
        TYPE_LISTING_REJECTED,
        TYPE_LISTING_EXPIRING,
        TYPE_LISTING_EXPIRED,
    }
)


def default_start_url() -> str:
    domain = getattr(settings, "APP_DOMAIN", "poisker.ru")
    return f"https://{domain}/"


def is_allowed_push_host(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower().rstrip(".")
    domain = getattr(settings, "APP_DOMAIN", "poisker.ru").lower()
    allowed = {domain, f"www.{domain}"}
    if host in allowed:
        return True
    return host.endswith(f".{domain}")


def sanitize_push_url(raw: str | None) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        return default_start_url()
    parsed = urlparse(candidate)
    if parsed.scheme != "https":
        return default_start_url()
    if not is_allowed_push_host(parsed.hostname):
        return default_start_url()
    return candidate


def bookmark_kind_to_push_type(kind: str) -> str:
    from bookmarks.models import Notification

    mapping = {
        Notification.KIND_MODERATION_APPROVED: TYPE_LISTING_APPROVED,
        Notification.KIND_MODERATION_REJECTED: TYPE_LISTING_REJECTED,
        Notification.KIND_POST_EXPIRED: TYPE_LISTING_EXPIRED,
        Notification.KIND_POST_UNPUBLISHED: TYPE_LISTING_EXPIRED,
    }
    return mapping.get(kind, TYPE_SYSTEM)


def preference_allows(pref, notification_type: str) -> bool:
    if notification_type == TYPE_MESSAGE:
        return pref.messages_enabled
    if notification_type in LISTING_KINDS:
        return pref.listings_enabled
    if notification_type == TYPE_MARKETING:
        return pref.marketing_enabled
    return pref.system_enabled
