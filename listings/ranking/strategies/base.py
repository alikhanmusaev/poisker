"""Shared scoring utilities for strategies."""

from __future__ import annotations

from dataclasses import dataclass, field

from listings.models import Post
from listings.ranking.config import ModeWeights
from listings.ranking import factors


@dataclass
class RankContext:
    query: str = ""
    category: str | None = None
    settlement_id: int | None = None
    region_id: int | None = None
    boost_city: str | None = None
    origin_lat: object = None
    origin_lon: object = None
    price_min: int | None = None
    price_max: int | None = None
    has_filters: bool = False
    expanded_terms: object = None
    limit: int = 20
    offset: int = 0
    page: int = 1


@dataclass
class RankingResult:
    mode: str
    results: list = field(default_factory=list)
    promoted: list = field(default_factory=list)
    sections: dict = field(default_factory=dict)
    total: int = 0
    local_total: int = 0
    geo_fallback: str | None = None
    geo_fallback_label: str = ""


def score_post(
    post: Post,
    weights: ModeWeights,
    *,
    relevance: float = 0.0,
    ctx: RankContext | None = None,
) -> float:
    ctx = ctx or RankContext()
    return (
        weights.relevance * relevance
        + weights.quality * factors.quality_factor(post)
        + weights.freshness * factors.freshness_factor(post)
        + weights.distance
        * factors.distance_factor(
            post,
            origin_lat=ctx.origin_lat,
            origin_lon=ctx.origin_lon,
            boost_city=ctx.boost_city,
        )
        + weights.engagement * factors.engagement_factor(post)
        + weights.promotion * factors.promotion_factor(post)
    )


def as_items(posts: list[Post], scores: dict | None = None) -> list[dict]:
    scores = scores or {}
    return [
        {"post": p, "highlight": {}, "score": scores.get(p.pk, p.rank_score or 0)}
        for p in posts
    ]
