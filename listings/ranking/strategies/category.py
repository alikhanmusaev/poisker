"""Category ranking: single organic list (promoted mixed via score)."""

from __future__ import annotations

from listings.ranking.config import get_ranking_settings
from listings.ranking.diversity import DiversityService
from listings.ranking.strategies.base import RankContext, RankingResult, score_post
from listings.services.geo_fallback import search_posts_with_geo_fallback


class CategoryRankingStrategy:
    mode = "category"

    def __init__(self):
        self.settings = get_ranking_settings()
        self.diversity = DiversityService(self.settings)

    def build(self, ctx: RankContext) -> RankingResult:
        found = search_posts_with_geo_fallback(
            query="",
            category=ctx.category,
            price_min=ctx.price_min,
            price_max=ctx.price_max,
            sort="rank",
            limit=max(80, ctx.offset + ctx.limit * 3),
            offset=0,
            settlement_id=ctx.settlement_id,
            region_id=ctx.region_id,
            boost_city=ctx.boost_city,
        )

        weights = self.settings.category
        organic = []
        for row in found.results:
            post = row.get("post")
            if post is None:
                continue
            organic.append(
                {
                    "post": post,
                    "highlight": {},
                    "score": score_post(post, weights, ctx=ctx),
                }
            )
        organic.sort(key=lambda x: x["score"], reverse=True)
        # Category page: all same category → skip category streak rule.
        organic = self.diversity.apply(organic, enforce_category=False)
        page_items = organic[ctx.offset : ctx.offset + ctx.limit]

        return RankingResult(
            mode=self.mode,
            promoted=[],
            results=page_items,
            sections={},
            total=max(found.total, len(organic)),
            local_total=found.local_total,
            geo_fallback=found.fallback,
            geo_fallback_label=found.fallback_label,
        )
