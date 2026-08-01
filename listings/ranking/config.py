"""Configurable ranking for Home / Category / Search modes."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ModeWeights:
    relevance: float = 0.0
    quality: float = 0.0
    freshness: float = 0.0
    distance: float = 0.0
    engagement: float = 0.0
    promotion: float = 0.0


@dataclass(frozen=True)
class RankingSettings:
    home_promoted_size: int
    category_promoted_size: int
    home_section_size: int
    home: ModeWeights
    category: ModeWeights
    search: ModeWeights
    search_filtered_promotion: float
    max_seller_per_screen: int
    max_same_category_in_row: int
    max_promoted_in_row: int
    diversity_enabled: bool
    promotion_rotation_enabled: bool


def get_ranking_settings() -> RankingSettings:
    return RankingSettings(
        home_promoted_size=int(getattr(settings, "HOME_PROMOTED_BLOCK_SIZE", 6)),
        category_promoted_size=int(getattr(settings, "CATEGORY_PROMOTED_BLOCK_SIZE", 6)),
        home_section_size=int(getattr(settings, "HOME_SECTION_SIZE", 8)),
        home=ModeWeights(
            quality=float(getattr(settings, "HOME_QUALITY_WEIGHT", 0.35)),
            freshness=float(getattr(settings, "HOME_FRESHNESS_WEIGHT", 0.30)),
            distance=float(getattr(settings, "HOME_DISTANCE_WEIGHT", 0.15)),
            engagement=float(getattr(settings, "HOME_ENGAGEMENT_WEIGHT", 0.15)),
            promotion=float(getattr(settings, "HOME_PROMOTION_WEIGHT", 0.05)),
        ),
        category=ModeWeights(
            quality=float(getattr(settings, "CATEGORY_QUALITY_WEIGHT", 0.40)),
            freshness=float(getattr(settings, "CATEGORY_FRESHNESS_WEIGHT", 0.25)),
            distance=float(getattr(settings, "CATEGORY_DISTANCE_WEIGHT", 0.15)),
            engagement=float(getattr(settings, "CATEGORY_ENGAGEMENT_WEIGHT", 0.10)),
            promotion=min(float(getattr(settings, "CATEGORY_PROMOTION_WEIGHT", 0.10)), 0.10),
        ),
        search=ModeWeights(
            relevance=float(getattr(settings, "SEARCH_RELEVANCE_WEIGHT", 0.55)),
            quality=float(getattr(settings, "SEARCH_QUALITY_WEIGHT", 0.20)),
            freshness=float(getattr(settings, "SEARCH_FRESHNESS_WEIGHT", 0.15)),
            distance=float(getattr(settings, "SEARCH_DISTANCE_WEIGHT", 0.05)),
            promotion=float(getattr(settings, "SEARCH_PROMOTION_WEIGHT", 0.05)),
        ),
        search_filtered_promotion=float(
            getattr(settings, "SEARCH_FILTERED_PROMOTION_WEIGHT", 0.03)
        ),
        max_seller_per_screen=int(getattr(settings, "MAX_SELLER_PER_SCREEN", 1)),
        max_same_category_in_row=int(getattr(settings, "MAX_SAME_CATEGORY_IN_ROW", 2)),
        max_promoted_in_row=int(getattr(settings, "MAX_PROMOTED_IN_ROW", 2)),
        diversity_enabled=bool(getattr(settings, "DIVERSITY_ENABLED", True)),
        promotion_rotation_enabled=bool(
            getattr(settings, "PROMOTION_ROTATION_ENABLED", True)
        ),
    )
