"""Category ranking: promoted block + organic list."""

from __future__ import annotations

from listings.ranking.config import get_ranking_settings
from listings.ranking.diversity import DiversityService
from listings.ranking.promotion_service import PromotionService
from listings.ranking.strategies.base import RankContext, RankingResult, as_items, score_post
from listings.services.geo_fallback import search_posts_with_geo_fallback


class CategoryRankingStrategy:
    mode = "category"

    def __init__(self):
        self.settings = get_ranking_settings()
        self.promotions = PromotionService()
        self.diversity = DiversityService(self.settings)

    def build(self, ctx: RankContext) -> RankingResult:
        promoted_posts = []
        if ctx.page <= 1:
            promoted_posts = self.promotions.promoted_for_block(
                limit=self.settings.category_promoted_size,
                category=ctx.category,
                settlement_id=ctx.settlement_id,
                region_id=ctx.region_id,
            )
        promoted_ids = {p.pk for p in promoted_posts}

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
            if post is None or post.pk in promoted_ids:
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
            promoted=as_items(promoted_posts),
            results=page_items,
            sections={},
            total=max(found.total - len(promoted_ids), len(organic)),
            local_total=found.local_total,
            geo_fallback=found.fallback,
            geo_fallback_label=found.fallback_label,
        )
