"""Search ranking: relevance first, tiny promo boost."""

from __future__ import annotations

from listings.ranking.config import ModeWeights, get_ranking_settings
from listings.ranking.diversity import DiversityService
from listings.ranking import factors
from listings.ranking.strategies.base import RankContext, RankingResult, score_post
from listings.services.geo_fallback import search_posts_with_geo_fallback
from listings.services.search import search_posts


class SearchRankingStrategy:
    mode = "search"

    def __init__(self):
        self.settings = get_ranking_settings()
        self.diversity = DiversityService(self.settings)

    def build(self, ctx: RankContext) -> RankingResult:
        weights = self.settings.search
        if ctx.has_filters:
            weights = ModeWeights(
                relevance=weights.relevance,
                quality=weights.quality,
                freshness=weights.freshness,
                distance=weights.distance,
                engagement=weights.engagement,
                promotion=self.settings.search_filtered_promotion,
            )

        # Prefer Typesense path when no settlement/region SQL forced.
        if ctx.settlement_id or ctx.region_id:
            found = search_posts_with_geo_fallback(
                query=ctx.query,
                category=ctx.category,
                price_min=ctx.price_min,
                price_max=ctx.price_max,
                sort="relevance",
                limit=max(100, ctx.offset + ctx.limit * 3),
                offset=0,
                expanded_terms=ctx.expanded_terms,
                settlement_id=ctx.settlement_id,
                region_id=ctx.region_id,
                boost_city=ctx.boost_city,
            )
            hits_as_rows = found.results
            total = found.total
            local_total = found.local_total
            fallback = found.fallback
            fallback_label = found.fallback_label
        else:
            rows, total = search_posts(
                query=ctx.query,
                category=ctx.category,
                price_min=ctx.price_min,
                price_max=ctx.price_max,
                sort="relevance",
                limit=max(100, ctx.offset + ctx.limit * 3),
                offset=0,
                expanded_terms=ctx.expanded_terms,
                boost_city=ctx.boost_city,
            )
            hits_as_rows = rows
            local_total = total
            fallback = None
            fallback_label = ""

        text_matches = []
        for row in hits_as_rows:
            # Typesense path may not expose text_match on already-reranked rows.
            text_matches.append(float(row.get("score") or 0) if isinstance(row.get("score"), (int, float)) else 0.0)
        # Use quality of title match proxy: prefer existing score only as weak signal.
        max_match = max(text_matches) if text_matches else 1.0

        scored = []
        for row, approx in zip(hits_as_rows, text_matches):
            post = row.get("post")
            if post is None:
                continue
            # Gate: promo must not outrank clearly better relevance.
            rel = factors.relevance_factor(max(approx, 0.01), max(max_match, 0.01))
            # If we only have rank-like scores, treat non-zero presence as mild relevance.
            if max_match <= 0:
                rel = 0.5
            score = score_post(post, weights, relevance=rel, ctx=ctx)
            scored.append({"post": post, "highlight": row.get("highlight") or {}, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        scored = self.diversity.apply(scored, enforce_category=True)
        page_items = scored[ctx.offset : ctx.offset + ctx.limit]

        return RankingResult(
            mode=self.mode,
            promoted=[],  # never a separate paid shelf in search
            results=page_items,
            sections={},
            total=total,
            local_total=local_total,
            geo_fallback=fallback,
            geo_fallback_label=fallback_label,
        )
