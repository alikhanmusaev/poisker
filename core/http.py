from django.conf import settings


def get_client_ip(request) -> str | None:
    """
    Client IP behind nginx.

    Prefer X-Real-IP ($remote_addr from nginx). Do not trust the left-most
    X-Forwarded-For hop — clients can prepend spoofed addresses.
    """
    if getattr(settings, "TRUST_PROXY", False):
        real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
        if real_ip:
            return real_ip
    return request.META.get("REMOTE_ADDR")
