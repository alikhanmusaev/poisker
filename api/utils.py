from django.conf import settings

from listings.services.posts import ValidationError as PostValidationError


def absolute_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    domain = getattr(settings, "APP_DOMAIN", "poisker.ru")
    return f"https://{domain}{path}"


def absolute_urls(paths: list[str]) -> list[str]:
    return [absolute_url(p) for p in paths if p]


def service_error(exc: Exception):
    from api.exceptions import ServiceValidationError

    if isinstance(exc, PostValidationError):
        raise ServiceValidationError(str(exc)) from exc
    raise exc


def parse_int_param(value, *, field: str):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        from rest_framework.exceptions import ValidationError

        raise ValidationError({field: ["Укажите целое число."]}) from exc
