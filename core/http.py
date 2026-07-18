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


def absolute_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    domain = getattr(settings, "APP_DOMAIN", "poisker.ru")
    return f"https://{domain}{path}"


def absolute_urls(paths: list[str]) -> list[str]:
    return [absolute_url(p) for p in paths if p]
