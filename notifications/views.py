"""HTTP API for FCM device registration (PWA + native)."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from notifications.models import PushDevice
from notifications.services import deactivate_device, register_device


def _json_body(request) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


@login_required
@require_POST
def register(request):
    payload = _json_body(request)
    token = str(payload.get("token") or "").strip()
    device_id = str(payload.get("device_id") or "").strip()
    platform = str(payload.get("platform") or PushDevice.PLATFORM_WEB).strip().lower()
    app_version = str(payload.get("app_version") or "")[:32]
    try:
        app_build = int(payload.get("app_build") or 0)
    except (TypeError, ValueError):
        app_build = 0

    if not token or not device_id:
        return JsonResponse({"ok": False, "error": "token_and_device_id_required"}, status=400)
    try:
        device = register_device(
            user=request.user,
            token=token,
            device_id=device_id,
            platform=platform,
            app_version=app_version,
            app_build=app_build,
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "device_id": device.device_id,
            "platform": device.platform,
            "active": device.active,
        }
    )


@login_required
@require_POST
def unregister(request):
    payload = _json_body(request)
    device_id = str(payload.get("device_id") or "").strip()
    if not device_id:
        return JsonResponse({"ok": False, "error": "device_id_required"}, status=400)
    ok = deactivate_device(user=request.user, device_id=device_id)
    return JsonResponse({"ok": ok})
