"""Device registration and FCM send services."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from notifications.models import NotificationPreference, PushDevice
from notifications.payloads import (
    TYPE_MESSAGE,
    preference_allows,
    sanitize_push_url,
)

logger = logging.getLogger(__name__)


def get_or_create_preferences(user) -> NotificationPreference:
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    return pref


def register_device(
    *,
    user,
    token: str,
    device_id: str,
    platform: str = PushDevice.PLATFORM_ANDROID,
    app_version: str = "",
    app_build: int = 0,
) -> PushDevice:
    token = (token or "").strip()
    device_id = (device_id or "").strip()
    if not token or not device_id:
        raise ValueError("token and device_id are required")
    if platform not in {PushDevice.PLATFORM_ANDROID, PushDevice.PLATFORM_IOS}:
        raise ValueError("unsupported platform")

    now = timezone.now()

    # Token may already belong to another user/device — rebind.
    existing_by_token = PushDevice.objects.filter(token=token).first()
    if existing_by_token and (
        existing_by_token.user_id != user.id or existing_by_token.device_id != device_id
    ):
        existing_by_token.delete()

    device, _created = PushDevice.objects.update_or_create(
        user=user,
        device_id=device_id,
        defaults={
            "token": token,
            "platform": platform,
            "app_version": (app_version or "")[:32],
            "app_build": max(0, int(app_build or 0)),
            "active": True,
            "failure_count": 0,
            "last_seen_at": now,
        },
    )
    get_or_create_preferences(user)
    return device


def deactivate_device(*, user, device_id: str) -> bool:
    device_id = (device_id or "").strip()
    if not device_id:
        return False
    updated = PushDevice.objects.filter(user=user, device_id=device_id, active=True).update(
        active=False,
        updated_at=timezone.now(),
    )
    return updated > 0


def send_push(
    user,
    title: str,
    body: str,
    url: str,
    notification_type: str,
    entity_id: str | None = None,
) -> dict[str, int]:
    """
    Send data-only FCM to all active devices of ``user``.
    Returns {"sent": N, "failed": M, "skipped": K}.
    """
    if not user or not getattr(user, "pk", None):
        return {"sent": 0, "failed": 0, "skipped": 1}

    pref = get_or_create_preferences(user)
    if not preference_allows(pref, notification_type):
        return {"sent": 0, "failed": 0, "skipped": 1}

    from notifications.firebase import ensure_firebase_app

    if not ensure_firebase_app():
        return {"sent": 0, "failed": 0, "skipped": 1}

    safe_url = sanitize_push_url(url)
    data = {
        "type": notification_type,
        "title": (title or "")[:200],
        "body": (body or "")[:500],
        "url": safe_url,
        "entity_id": str(entity_id or ""),
    }

    devices = list(
        PushDevice.objects.filter(user=user, active=True).only("id", "token", "failure_count")
    )
    if not devices:
        return {"sent": 0, "failed": 0, "skipped": 0}

    sent = failed = 0
    for device in devices:
        ok = _send_to_token(device, data)
        if ok:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed, "skipped": 0}


def schedule_push(
    user_id: int,
    *,
    title: str,
    body: str,
    url: str,
    notification_type: str,
    entity_id: str | None = None,
) -> None:
    """Enqueue push after the surrounding DB transaction commits."""

    def _run():
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return
        try:
            send_push(
                user,
                title=title,
                body=body,
                url=url,
                notification_type=notification_type,
                entity_id=entity_id,
            )
        except Exception:
            logger.exception("schedule_push failed for user_id=%s", user_id)

    transaction.on_commit(_run)


def _send_to_token(device: PushDevice, data: dict[str, str]) -> bool:
    from firebase_admin import messaging
    from firebase_admin.exceptions import FirebaseError
    from firebase_admin.messaging import UnregisteredError

    message = messaging.Message(
        data={k: str(v) for k, v in data.items()},
        token=device.token,
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        messaging.send(message)
        PushDevice.objects.filter(pk=device.pk).update(
            failure_count=0,
            last_seen_at=timezone.now(),
        )
        return True
    except UnregisteredError:
        PushDevice.objects.filter(pk=device.pk).update(active=False)
        return False
    except FirebaseError as exc:
        code = getattr(exc, "code", "") or ""
        # Invalid / not-found tokens
        if "registration-token-not-registered" in str(exc).lower() or code in {
            "NOT_FOUND",
            "UNREGISTERED",
        }:
            PushDevice.objects.filter(pk=device.pk).update(active=False)
        else:
            PushDevice.objects.filter(pk=device.pk).update(
                failure_count=device.failure_count + 1,
            )
        logger.warning("FCM send failed code=%s", code or type(exc).__name__)
        return False
    except Exception:
        PushDevice.objects.filter(pk=device.pk).update(
            failure_count=device.failure_count + 1,
        )
        logger.exception("FCM send unexpected error")
        return False


def push_for_bookmark_notification(
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    post=None,
    payload: dict[str, Any] | None = None,
) -> None:
    from core.http import absolute_url
    from listings.services.seo_urls import post_public_url
    from notifications.payloads import bookmark_kind_to_push_type

    notification_type = bookmark_kind_to_push_type(kind)
    if post is not None:
        url = absolute_url(post_public_url(post))
        entity_id = str(post.pk)
    else:
        url = absolute_url("/notifications/")
        entity_id = str((payload or {}).get("entity_id") or "")
    schedule_push(
        user_id,
        title=title,
        body=body,
        url=url,
        notification_type=notification_type,
        entity_id=entity_id,
    )


def push_for_new_message(*, recipient, conversation, sender, message) -> None:
    from core.http import absolute_url

    preview = (message.body or "").strip()
    if not preview and message.image:
        preview = "Фотография"
    preview = preview[:120] or "Новое сообщение"
    title = "Новое сообщение"
    body = f"{getattr(sender, 'display_name', None) or 'Пользователь'}: {preview}"
    url = absolute_url(f"/messages/{conversation.pk}/")
    schedule_push(
        recipient.pk,
        title=title,
        body=body,
        url=url,
        notification_type=TYPE_MESSAGE,
        entity_id=str(conversation.pk),
    )


def notify_listing_expiring(*, days: int = 3) -> int:
    """Notify sellers whose published posts expire within ``days`` (once per post)."""
    from datetime import timedelta

    from django.core.cache import cache
    from django.utils import timezone

    from core.http import absolute_url
    from listings.models import Post
    from listings.services.seo_urls import post_public_url
    from notifications.payloads import TYPE_LISTING_EXPIRING

    now = timezone.now()
    until = now + timedelta(days=days)
    qs = Post.objects.filter(
        status="published",
        expires_at__gt=now,
        expires_at__lte=until,
    ).select_related("user")
    count = 0
    for post in qs.iterator():
        cache_key = f"push:listing_expiring:{post.pk}"
        if cache.get(cache_key):
            continue
        schedule_push(
            post.user_id,
            title="Срок объявления заканчивается",
            body=f"«{post.title}» скоро будет снято с публикации.",
            url=absolute_url(post_public_url(post)),
            notification_type=TYPE_LISTING_EXPIRING,
            entity_id=str(post.pk),
        )
        cache.set(cache_key, "1", timeout=days * 86400 + 86400)
        count += 1
    return count
