from __future__ import annotations

from listings.ranking.factors import origin_coords
from listings.ranking.strategies.base import RankContext, RankingResult
from listings.ranking.strategies.category import CategoryRankingStrategy
from listings.ranking.strategies.home import HomeRankingStrategy
from listings.ranking.strategies.search import SearchRankingStrategy


class RankingService:
    """Facade selecting Home / Category / Search strategies."""

    def __init__(self):
        self.home = HomeRankingStrategy()
        self.category = CategoryRankingStrategy()
        self.search = SearchRankingStrategy()

    def resolve_mode(self, *, query: str, category: str | None) -> str:
        if query:
            return "search"
        if category:
            return "category"
        return "home"

    def build(
        self,
        *,
        query: str = "",
        category: str | None = None,
        settlement=None,
        region=None,
        boost_city: str | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        has_filters: bool = False,
        expanded_terms=None,
        limit: int = 20,
        offset: int = 0,
        page: int = 1,
        mode: str | None = None,
    ) -> RankingResult:
        lat, lon = origin_coords(settlement)
        settlement_id = settlement.id if settlement is not None else None
        region_id = None
        if settlement is None and region is not None:
            region_id = region.id
        elif settlement is not None and region is None:
            # Prefer settlement filter only; region used for promo widen inside services if needed.
            region_id = None

        ctx = RankContext(
            query=query or "",
            category=category or None,
            settlement_id=settlement_id,
            region_id=region_id,
            boost_city=boost_city,
            origin_lat=lat,
            origin_lon=lon,
            price_min=price_min,
            price_max=price_max,
            has_filters=has_filters,
            expanded_terms=expanded_terms,
            limit=limit,
            offset=offset,
            page=page,
        )
        chosen = mode or self.resolve_mode(query=ctx.query, category=ctx.category)
        if chosen == "search":
            return self.search.build(ctx)
        if chosen == "category":
            return self.category.build(ctx)
        return self.home.build(ctx)
