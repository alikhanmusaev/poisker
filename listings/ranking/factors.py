"""Factor helpers for ranking strategies."""

from __future__ import annotations

import math
from decimal import Decimal

from listings.models import Post
from listings.services.ranking import (
    engagement_score as base_engagement,
    freshness_score,
)


def quality_factor(post: Post) -> float:
    score = float(post.rank_score or 0.0)
    if score > 0:
        return min(score, 1.0)
    # Fallback if rank_score not yet calculated.
    from listings.services.ranking import calculate_rank_score

    return min(calculate_rank_score(post), 1.0)


def freshness_factor(post: Post) -> float:
    return freshness_score(post.created_at, getattr(post, "bumped_at", None))


def engagement_factor(post: Post) -> float:
    return base_engagement(post)


def promotion_factor(post: Post) -> float:
    return 1.0 if post.is_promoted else 0.0


def distance_factor(post: Post, *, origin_lat=None, origin_lon=None, boost_city: str | None = None) -> float:
    """1.0 = same place / nearby; 0.0 = far or unknown."""
    if boost_city and post.city == boost_city:
        return 1.0
    if origin_lat is None or origin_lon is None:
        return 0.0
    plat = getattr(getattr(post, "settlement", None), "latitude", None)
    plon = getattr(getattr(post, "settlement", None), "longitude", None)
    if plat is None or plon is None:
        return 0.0
    km = _haversine_km(float(origin_lat), float(origin_lon), float(plat), float(plon))
    # Soft falloff: full score within 15km, near-zero after ~120km.
    return max(0.0, 1.0 - min(km / 120.0, 1.0))


def relevance_factor(text_match: float, max_text_match: float) -> float:
    if not text_match or max_text_match <= 0:
        return 0.0
    return min(math.log1p(float(text_match)) / math.log1p(max_text_match), 1.0)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def origin_coords(settlement) -> tuple[Decimal | None, Decimal | None]:
    if settlement is None:
        return None, None
    return settlement.latitude, settlement.longitude
