"""Remember the visitor's preferred city for feed filtering and geo-boost."""

from django.conf import settings

from listings.constants import CITIES

PREFERRED_CITY_COOKIE = "poisker_city"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 days


def preferred_city_from_request(request) -> str | None:
    raw = (request.COOKIES.get(PREFERRED_CITY_COOKIE) or "").strip()
    return raw if raw in CITIES else None


def resolve_boost_city(request, *, filtered_city: str | None) -> str | None:
    """Boost only when the listing is not already hard-filtered by city."""
    if filtered_city:
        return None
    return preferred_city_from_request(request)


def _cookie_kwargs():
    return {
        "max_age": COOKIE_MAX_AGE,
        "samesite": "Lax",
        "secure": bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        "httponly": False,
        "path": "/",
    }


def attach_city_cookie(response, city: str | None):
    if not city or city not in CITIES:
        return response
    response.set_cookie(PREFERRED_CITY_COOKIE, city, **_cookie_kwargs())
    return response


def clear_city_cookie(response):
    response.delete_cookie(
        PREFERRED_CITY_COOKIE,
        path="/",
        samesite="Lax",
    )
    return response
