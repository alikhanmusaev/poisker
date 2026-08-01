"""Widen geography when a strict city/region search returns nothing."""

from __future__ import annotations

from dataclasses import dataclass

from locations.models import Settlement
from listings.services.search import search_posts


@dataclass(frozen=True)
class GeoFallbackResult:
    results: list
    total: int
    local_total: int
    fallback: str | None  # None | "region" | "all"
    fallback_label: str = ""


def search_posts_with_geo_fallback(
    *,
    query: str = "",
    city: str | None = None,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    sort: str = "rank",
    limit: int = 20,
    offset: int = 0,
    expanded_terms=None,
    boost_city: str | None = None,
    settlement_id: int | None = None,
    region_id: int | None = None,
    settlement_name: str = "",
    region_name: str = "",
) -> GeoFallbackResult:
    """
    Strict geo first; if empty, widen settlement → region → all Russia.
    """
    common = dict(
        query=query,
        category=category,
        price_min=price_min,
        price_max=price_max,
        with_photo=with_photo,
        with_price=with_price,
        sort=sort,
        limit=limit,
        offset=offset,
        expanded_terms=expanded_terms,
        boost_city=boost_city,
    )

    results, total = search_posts(
        city=city,
        settlement_id=settlement_id,
        region_id=region_id,
        **common,
    )
    local_total = total
    if total > 0 or (settlement_id is None and region_id is None and not city):
        return GeoFallbackResult(
            results=results,
            total=total,
            local_total=local_total,
            fallback=None,
        )

    # Settlement (or legacy city) empty → try region.
    widen_region_id = region_id
    if settlement_id and not widen_region_id:
        row = (
            Settlement.objects.filter(pk=settlement_id)
            .select_related("region")
            .first()
        )
        if row is not None:
            widen_region_id = row.region_id
            if not region_name:
                region_name = row.region.name
            if not settlement_name:
                settlement_name = row.name

    if widen_region_id:
        results, total = search_posts(
            city=None,
            settlement_id=None,
            region_id=widen_region_id,
            **common,
        )
        if total > 0:
            place = settlement_name or "выбранном городе"
            label = (
                f"В {place} ничего не нашлось — показываем объявления "
                f"по региону {region_name or 'региону'}."
            )
            return GeoFallbackResult(
                results=results,
                total=total,
                local_total=local_total,
                fallback="region",
                fallback_label=label,
            )

    # Still empty → all Russia.
    results, total = search_posts(
        city=None,
        settlement_id=None,
        region_id=None,
        **common,
    )
    if total > 0:
        if settlement_name:
            place = settlement_name
        elif region_name:
            place = region_name
        else:
            place = "выбранном месте"
        label = (
            f"В {place} ничего не нашлось — показываем объявления по всей России."
        )
        return GeoFallbackResult(
            results=results,
            total=total,
            local_total=local_total,
            fallback="all",
            fallback_label=label,
        )

    return GeoFallbackResult(
        results=results,
        total=total,
        local_total=local_total,
        fallback=None,
    )
