from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from locations.models import Region, Settlement

SEARCH_MIN_LEN = 2
SEARCH_DEFAULT_LIMIT = 20
SEARCH_CACHE_TTL = 120


def _one_character_shorter_queries(query: str) -> set[str]:
    """Return useful typo variants for a locality lookup.

    Mobile keyboards make a single omitted character common ("Атуры" instead
    of "Автуры"). Keep this conservative: it is only a fallback after an
    exact substring lookup and is never used for very short queries.
    """
    if len(query) < 4:
        return set()
    return {f"{query[:index]}{query[index + 1:]}" for index in range(len(query))}


def search_settlements(
    query: str,
    *,
    region_id: int | None = None,
    region_slug: str | None = None,
    limit: int = SEARCH_DEFAULT_LIMIT,
) -> list[Settlement]:
    q = (query or "").strip()
    if len(q) < SEARCH_MIN_LEN:
        return []

    limit = max(1, min(int(limit or SEARCH_DEFAULT_LIMIT), 20))
    cache_key = f"loc:search:v2:{region_id or region_slug or '-'}:{limit}:{q.lower()}"
    cached_ids = cache.get(cache_key)
    if cached_ids is not None:
        preserved = {pk: i for i, pk in enumerate(cached_ids)}
        rows = list(
            Settlement.objects.filter(pk__in=cached_ids, is_active=True)
            .select_related("region")
            .filter(region__is_active=True)
        )
        if len(rows) == len(cached_ids):
            rows.sort(key=lambda s: preserved.get(s.pk, 10_000))
            return rows

    qs: QuerySet[Settlement] = (
        Settlement.objects.filter(is_active=True, region__is_active=True)
        .select_related("region")
    )
    if region_id:
        qs = qs.filter(region_id=region_id)
    elif region_slug:
        qs = qs.filter(region__slug=region_slug)

    exact_matches = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    if exact_matches.exists():
        qs = exact_matches
    else:
        # Fallback for one omitted character. It runs only when the regular
        # query has no results, so common searches retain indexed lookup.
        shorter_queries = _one_character_shorter_queries(q)
        if not shorter_queries:
            return []
        fuzzy_filter = Q()
        for variant in shorter_queries:
            fuzzy_filter |= Q(name__icontains=variant) | Q(slug__icontains=variant)
        qs = qs.filter(fuzzy_filter)

    qs = qs.annotate(
        rank=Case(
            When(name__iexact=q, then=Value(0)),
            When(name__istartswith=q, then=Value(1)),
            When(slug__istartswith=q, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("rank", "-population", "name")[:limit]

    rows = list(qs)
    cache.set(cache_key, [s.pk for s in rows], SEARCH_CACHE_TTL)
    return rows


def settlement_to_dict(s: Settlement) -> dict:
    return {
        "kind": "settlement",
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "type": s.type,
        "region": {
            "id": s.region_id,
            "name": s.region.name,
            "slug": s.region.slug,
            "code": s.region.code,
        },
        "display_name": s.display_name,
    }


def search_regions(query: str, *, limit: int = 8) -> list[Region]:
    """Return matching regions so visitors can search an entire region directly."""
    q = (query or "").strip()
    if len(q) < SEARCH_MIN_LEN:
        return []

    limit = max(1, min(int(limit or 8), 12))
    return list(
        Region.objects.filter(is_active=True)
        .filter(Q(name__icontains=q) | Q(slug__icontains=q))
        .annotate(
            rank=Case(
                When(name__iexact=q, then=Value(0)),
                When(name__istartswith=q, then=Value(1)),
                When(slug__istartswith=q, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "name")[:limit]
    )


def region_to_dict(region: Region) -> dict:
    return {
        "kind": "region",
        "id": region.id,
        "name": region.name,
        "slug": region.slug,
        "display_name": region.name,
    }


def popular_settlements(limit: int = 16) -> list[Settlement]:
    limit = max(1, min(limit, 30))
    cache_key = f"loc:popular:v1:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return list(
            Settlement.objects.filter(pk__in=cached, is_active=True)
            .select_related("region")
            .order_by("-population", "name")
        )
    rows = list(
        Settlement.objects.filter(is_active=True, is_popular=True, region__is_active=True)
        .select_related("region")
        .order_by("-population", "name")[:limit]
    )
    if len(rows) < limit:
        # Fallback: largest settlements
        extra = (
            Settlement.objects.filter(is_active=True, region__is_active=True)
            .exclude(pk__in=[r.pk for r in rows])
            .select_related("region")
            .order_by("-population", "name")[: limit - len(rows)]
        )
        rows.extend(extra)
    cache.set(cache_key, [s.pk for s in rows], 600)
    return rows


def default_fallback_settlement() -> Settlement | None:
    """Legacy Poisker default: Grozny."""
    return (
        Settlement.objects.filter(slug="grozny", region__code="12", is_active=True)
        .select_related("region")
        .first()
    )
