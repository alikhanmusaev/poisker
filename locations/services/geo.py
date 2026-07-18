"""Resolve visitor geography: settlement / region / all Russia."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from locations.models import Region, Settlement

COOKIE_SETTLEMENT = "poisker_settlement_id"
COOKIE_REGION = "poisker_region_id"
COOKIE_SCOPE = "poisker_geo_scope"  # settlement | region | russia
COOKIE_MAX_AGE = 60 * 60 * 24 * 180
LEGACY_CITY_COOKIE = "poisker_city"


@dataclass
class GeoSelection:
    scope: str  # settlement | region | russia
    settlement: Settlement | None = None
    region: Region | None = None

    @property
    def label(self) -> str:
        if self.scope == "settlement" and self.settlement:
            return self.settlement.name
        if self.scope == "region" and self.region:
            return self.region.name
        return "Вся Россия"

    @property
    def subtitle(self) -> str:
        if self.scope == "settlement" and self.settlement:
            return self.settlement.region.name
        if self.scope == "region" and self.region:
            return "Регион"
        return "Россия"


def _cookie_kwargs():
    return {
        "max_age": COOKIE_MAX_AGE,
        "samesite": "Lax",
        "secure": bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        "httponly": False,
        "path": "/",
    }


def resolve_geo(
    request,
    *,
    url_settlement: Settlement | None = None,
    url_region: Region | None = None,
) -> GeoSelection:
    """Priority: URL fix > query > cookies > user profile > legacy city > russia."""
    if url_settlement is not None:
        return GeoSelection(
            "settlement", settlement=url_settlement, region=url_settlement.region
        )
    if url_region is not None:
        return GeoSelection("region", region=url_region)

    if (request.GET.get("geo") or "").strip() == "russia":
        return GeoSelection("russia")

    sid = request.GET.get("settlement") or request.COOKIES.get(COOKIE_SETTLEMENT)
    if sid and str(sid).isdigit():
        s = (
            Settlement.objects.filter(
                pk=int(sid), is_active=True, region__is_active=True
            )
            .select_related("region")
            .first()
        )
        if s:
            return GeoSelection("settlement", settlement=s, region=s.region)

    rid = request.GET.get("region") or request.COOKIES.get(COOKIE_REGION)
    if rid and str(rid).isdigit():
        r = Region.objects.filter(pk=int(rid), is_active=True).first()
        if r:
            return GeoSelection("region", region=r)

    if (request.COOKIES.get(COOKIE_SCOPE) or "").strip() == "russia":
        return GeoSelection("russia")

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        pref_id = getattr(user, "preferred_settlement_id", None)
        if pref_id:
            pref = (
                Settlement.objects.filter(pk=pref_id, is_active=True)
                .select_related("region")
                .first()
            )
            if pref:
                return GeoSelection("settlement", settlement=pref, region=pref.region)

    legacy = (request.COOKIES.get(LEGACY_CITY_COOKIE) or "").strip()
    if legacy:
        s = (
            Settlement.objects.filter(
                slug=legacy, is_active=True, region__code="12"
            )
            .select_related("region")
            .first()
        )
        if s:
            return GeoSelection("settlement", settlement=s, region=s.region)

    return GeoSelection("russia")


def apply_geo_filter(queryset, geo: GeoSelection):
    if geo.scope == "settlement" and geo.settlement is not None:
        return queryset.filter(settlement_id=geo.settlement.id)
    if geo.scope == "region" and geo.region is not None:
        return queryset.filter(settlement__region_id=geo.region.id)
    # All Russia: also include legacy posts without settlement yet (city slug only)
    return queryset


def attach_geo_cookies(response, geo: GeoSelection):
    kwargs = _cookie_kwargs()
    response.set_cookie(COOKIE_SCOPE, geo.scope, **kwargs)
    if geo.settlement is not None:
        response.set_cookie(COOKIE_SETTLEMENT, str(geo.settlement.id), **kwargs)
        response.set_cookie(LEGACY_CITY_COOKIE, geo.settlement.slug, **kwargs)
    else:
        response.delete_cookie(COOKIE_SETTLEMENT, path="/", samesite="Lax")
    if geo.region is not None:
        response.set_cookie(COOKIE_REGION, str(geo.region.id), **kwargs)
    else:
        response.delete_cookie(COOKIE_REGION, path="/", samesite="Lax")
    return response


def clear_geo_cookies(response):
    kwargs = _cookie_kwargs()
    response.delete_cookie(COOKIE_SETTLEMENT, path="/", samesite="Lax")
    response.delete_cookie(COOKIE_REGION, path="/", samesite="Lax")
    response.delete_cookie(LEGACY_CITY_COOKIE, path="/", samesite="Lax")
    response.set_cookie(COOKIE_SCOPE, "russia", **kwargs)
    return response
