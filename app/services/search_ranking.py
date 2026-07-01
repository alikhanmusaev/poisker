import math
import re
from typing import Literal

from app.models import Post
from app.services.ranking import freshness_score

Mode = Literal["feed", "search"]

FEED_WEIGHTS = {
    "relevance": 0.0,
    "rank": 0.55,
    "fresh": 0.25,
    "promo": 0.15,
    "exact": 0.0,
    "price": 0.05,
}

SEARCH_WEIGHTS = {
    "relevance": 0.45,
    "rank": 0.25,
    "fresh": 0.10,
    "promo": 0.10,
    "exact": 0.08,
    "price": 0.02,
}

HYBRID_SORTS = frozenset({"rank", "relevance"})


def uses_hybrid_ranking(sort: str) -> bool:
    return sort in HYBRID_SORTS


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower().replace("ё", "е")).strip()


def normalize_relevance(text_match: int | float, max_match: float) -> float:
    if not text_match or max_match <= 0:
        return 0.0
    return min(math.log1p(float(text_match)) / math.log1p(max_match), 1.0)


def normalize_rank_score(rank_score: float | None) -> float:
    if not rank_score or rank_score <= 0:
        return 0.0
    return min(float(rank_score), 1.0)


def exact_title_bonus(query: str, title: str) -> float:
    q = _norm(query)
    t = _norm(title)
    if not q or not t:
        return 0.0
    if q in t:
        return 1.0
    tokens = [token for token in q.split() if len(token) >= 2]
    if not tokens:
        return 0.0
    if all(token in t for token in tokens):
        return 0.5
    return 0.0


def price_fit_bonus(
    price_min: int | None,
    price_max: int | None,
    post_price: int | None,
) -> float:
    if post_price is None:
        return 0.0
    if price_max is not None and price_max > 0:
        return max(0.0, 1.0 - min(abs(post_price - price_max) / price_max, 1.0))
    if price_min is not None and price_min > 0:
        if post_price >= price_min:
            return min(1.0, post_price / (price_min * 2))
    return 0.0


def promotion_boost(post: Post) -> float:
    return 1.0 if post.is_promoted else 0.0


def compute_final_score(
    post: Post,
    text_match: int | float,
    *,
    query: str,
    mode: Mode,
    max_text_match: float,
    price_min: int | None = None,
    price_max: int | None = None,
) -> float:
    weights = SEARCH_WEIGHTS if mode == "search" else FEED_WEIGHTS
    relevance = normalize_relevance(text_match, max_text_match)
    rank = normalize_rank_score(post.rank_score)
    fresh = freshness_score(post.created_at)
    promo = promotion_boost(post)
    exact = exact_title_bonus(query, post.title) if query else 0.0
    price = price_fit_bonus(price_min, price_max, post.price)

    return (
        weights["relevance"] * relevance
        + weights["rank"] * rank
        + weights["fresh"] * fresh
        + weights["promo"] * promo
        + weights["exact"] * exact
        + weights["price"] * price
    )


def rerank_hits(
    hits: list[dict],
    posts_map: dict[str, Post],
    *,
    query: str,
    mode: Mode,
    sort: str,
    price_min: int | None = None,
    price_max: int | None = None,
    extract_highlight,
) -> list[dict]:
    if not hits:
        return []

    max_text_match = max((hit.get("text_match", 0) or 0 for hit in hits), default=0)
    results = []
    for hit in hits:
        doc = hit.get("document", {})
        post = posts_map.get(doc.get("id"))
        if not post:
            continue
        text_match = hit.get("text_match", 0) or 0
        if uses_hybrid_ranking(sort):
            score = compute_final_score(
                post,
                text_match,
                query=query,
                mode=mode,
                max_text_match=max_text_match,
                price_min=price_min,
                price_max=price_max,
            )
        elif sort == "date_desc":
            score = float(post.created_at.timestamp()) if post.created_at else 0.0
        elif sort == "price_asc":
            price_val = float(post.price) if post.price is not None else float("inf")
            tie = compute_final_score(
                post,
                text_match,
                query=query,
                mode=mode,
                max_text_match=max_text_match,
                price_min=price_min,
                price_max=price_max,
            )
            score = (price_val, -tie)
        elif sort == "price_desc":
            price_val = float(-post.price) if post.price is not None else float("inf")
            tie = compute_final_score(
                post,
                text_match,
                query=query,
                mode=mode,
                max_text_match=max_text_match,
                price_min=price_min,
                price_max=price_max,
            )
            score = (price_val, -tie)
        else:
            score = compute_final_score(
                post,
                text_match,
                query=query,
                mode=mode,
                max_text_match=max_text_match,
                price_min=price_min,
                price_max=price_max,
            )

        results.append({
            "post": post,
            "highlight": extract_highlight(hit),
            "score": score,
        })

    if sort in ("price_asc", "price_desc"):
        reverse = False
    else:
        reverse = True
    results.sort(key=lambda item: item["score"], reverse=reverse)
    return results
