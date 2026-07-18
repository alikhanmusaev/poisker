"""Compatibility aliases for the location-based geo selection service."""

from locations.services.geo import (
    COOKIE_MAX_AGE,
    LEGACY_CITY_COOKIE,
    attach_geo_cookies,
    clear_geo_cookies,
    resolve_geo,
)

PREFERRED_CITY_COOKIE = LEGACY_CITY_COOKIE


def preferred_city_from_request(request) -> str | None:
    """Return the legacy city slug, including a valid settlement preference."""
    raw = (request.COOKIES.get(PREFERRED_CITY_COOKIE) or "").strip()
    if raw:
        return raw
    geo = resolve_geo(request)
    return geo.settlement.slug if geo.settlement is not None else None


def resolve_boost_city(request, *, filtered_city: str | None) -> str | None:
    return None if filtered_city else preferred_city_from_request(request)


def attach_city_cookie(response, city: str | None):
    if city:
        response.set_cookie(
            PREFERRED_CITY_COOKIE, city, max_age=COOKIE_MAX_AGE, samesite="Lax", path="/"
        )
    return response


def clear_city_cookie(response):
    return clear_geo_cookies(response)
