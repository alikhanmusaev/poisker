"""Home page ranking: new / popular / recommended (promoted mixed via score)."""

from __future__ import annotations

from django.utils import timezone

from listings.models import Post
from listings.ranking.config import get_ranking_settings
from listings.ranking.diversity import DiversityService
from listings.ranking.strategies.base import RankContext, RankingResult, score_post
from listings.services.geo_fallback import search_posts_with_geo_fallback


class HomeRankingStrategy:
    mode = "home"

    def __init__(self):
        self.settings = get_ranking_settings()
        self.diversity = DiversityService(self.settings)

    def build(self, ctx: RankContext) -> RankingResult:
        # Candidate pool via existing search + geo fallback (organic browse).
        found = search_posts_with_geo_fallback(
            query="",
            category=ctx.category,
            price_min=ctx.price_min,
            price_max=ctx.price_max,
            sort="date_desc",
            limit=120,
            offset=0,
            settlement_id=ctx.settlement_id,
            region_id=ctx.region_id,
            boost_city=ctx.boost_city,
        )
        candidates = [row["post"] for row in found.results if row.get("post") is not None]
        # Top up from ORM if needed.
        if len(candidates) < 40:
            now = timezone.now()
            qs = Post.objects.filter(status="published", expires_at__gte=now).select_related(
                "user", "settlement", "settlement__region"
            )
            if ctx.category:
                qs = qs.filter(category=ctx.category)
            if ctx.settlement_id:
                qs = qs.filter(settlement_id=ctx.settlement_id)
            elif ctx.region_id:
                qs = qs.filter(settlement__region_id=ctx.region_id)
            qs = qs.exclude(pk__in={p.pk for p in candidates})
            candidates.extend(list(qs.order_by("-created_at")[:80]))

        weights = self.settings.home
        scored = []
        for post in candidates:
            scored.append(
                {
                    "post": post,
                    "highlight": {},
                    "score": score_post(post, weights, ctx=ctx),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)

        section_size = self.settings.home_section_size
        used: set = set()

        def take(pool: list[dict], n: int, key_fn) -> list[dict]:
            ordered = sorted(pool, key=key_fn, reverse=True)
            picked = []
            for item in ordered:
                post = item["post"]
                if post.pk in used:
                    continue
                picked.append(item)
                used.add(post.pk)
                if len(picked) >= n:
                    break
            return self.diversity.apply(picked, enforce_category=True)

        new_items = take(
            scored,
            section_size,
            key_fn=lambda it: it["post"].created_at.timestamp() if it["post"].created_at else 0,
        )
        popular_items = take(
            scored,
            section_size,
            key_fn=lambda it: (
                (it["post"].views or 0) + 3 * (it["post"].contact_clicks or 0),
                it["score"],
            ),
        )
        recommended_items = take(
            scored,
            section_size,
            key_fn=lambda it: it["score"],
        )

        # Flat results for pagination / HTMX consumers: recommended-first organic.
        organic = self.diversity.apply(scored, enforce_category=True)
        page_items = organic[ctx.offset : ctx.offset + ctx.limit]

        return RankingResult(
            mode=self.mode,
            promoted=[],
            results=page_items,
            sections={
                "new": new_items,
                "popular": popular_items,
                "recommended": recommended_items,
            },
            total=max(found.local_total, len(organic)),
            local_total=found.local_total,
            geo_fallback=found.fallback,
            geo_fallback_label=found.fallback_label,
        )
