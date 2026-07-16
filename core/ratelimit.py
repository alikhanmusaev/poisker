"""Shared Redis/LocMem rate limiting helpers."""

from __future__ import annotations

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def is_rate_limited(key: str, *, limit: int, window_seconds: int, fail_closed: bool = False) -> bool:
    """
    Increment a counter for `key` and return True if the caller should be blocked.

    Uses cache.add + cache.incr so the window is shared across gunicorn workers
    when Redis is configured as CACHES default.
    """
    if limit <= 0:
        return False
    try:
        if cache.add(key, 1, window_seconds):
            return False
        count = cache.incr(key)
        return int(count) > limit
    except Exception:
        logger.exception("Rate limit cache error for %s", key)
        return bool(fail_closed)


def hit_rate_limit(key: str, *, limit: int, window_seconds: int, fail_closed: bool = False) -> bool:
    """Alias kept for call-site clarity — True means over limit."""
    return is_rate_limited(key, limit=limit, window_seconds=window_seconds, fail_closed=fail_closed)
