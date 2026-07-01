import typesense
from flask import current_app
from markupsafe import Markup, escape
from sqlalchemy import nullslast, or_

from app.constants import (
    BRAND_ALIASES,
    CATEGORIES,
    CITIES,
    DEFAULT_SEARCH_SORT,
    DEFAULT_SORT,
    POPULAR_SUGGESTIONS,
    SEARCH_SYNONYMS,
    SORT_OPTIONS,
)
from app.models import Post, utcnow
from app.services.search_ranking import rerank_hits, uses_hybrid_ranking
from app.services.smart_query import parse_search_query, smart_suggestions


COLLECTION_NAME = "posts"
CANDIDATE_MIN = 60
CANDIDATE_MAX = 250
PRICE_SUGGEST_THRESHOLDS = (
    5_000,
    10_000,
    15_000,
    20_000,
    30_000,
    50_000,
    75_000,
    100_000,
    150_000,
    200_000,
    500_000,
    1_000_000,
)


def _live_posts_query(q):
    return q.filter(Post.expires_at >= utcnow())


def _collection_schema() -> dict:
    return {
        "name": COLLECTION_NAME,
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "body", "type": "string"},
            {"name": "category", "type": "string", "facet": True},
            {"name": "city", "type": "string", "facet": True},
            {"name": "price", "type": "int32", "optional": True},
            {"name": "status", "type": "string", "facet": True},
            {"name": "has_photo", "type": "bool", "facet": True},
            {"name": "rank_score", "type": "float"},
            {"name": "created_at", "type": "int64"},
            {"name": "paid_boost", "type": "float", "optional": True},
        ],
        "default_sorting_field": "rank_score",
        "token_separators": ["-", "_"],
    }


def _typesense_sort(sort: str, has_query: bool) -> str | None:
    if has_query and uses_hybrid_ranking(sort):
        return None
    if sort == "price_asc":
        return "price:asc,rank_score:desc,created_at:desc"
    if sort == "price_desc":
        return "price:desc,rank_score:desc,created_at:desc"
    if sort == "date_desc":
        return "created_at:desc"
    return "rank_score:desc,created_at:desc"


def _apply_sql_sort(q, sort: str):
    if sort == "price_asc":
        return q.order_by(nullslast(Post.price.asc()), Post.rank_score.desc(), Post.created_at.desc())
    if sort == "price_desc":
        return q.order_by(nullslast(Post.price.desc()), Post.rank_score.desc(), Post.created_at.desc())
    if sort == "date_desc":
        return q.order_by(Post.created_at.desc())
    return q.order_by(Post.rank_score.desc(), Post.created_at.desc())


def _candidate_limit(limit: int, offset: int) -> int:
    return min(max(CANDIDATE_MIN, (offset + limit) * 3), CANDIDATE_MAX)


def get_typesense_client():
    from urllib.parse import urlparse

    url = urlparse(current_app.config["TYPESENSE_URL"])
    host = url.hostname or "localhost"
    port = str(url.port or 8108)
    protocol = url.scheme or "http"
    return typesense.Client(
        {
            "nodes": [{"host": host, "port": port, "protocol": protocol}],
            "api_key": current_app.config["TYPESENSE_API_KEY"],
            "connection_timeout_seconds": 5,
        }
    )


def _sync_synonyms():
    client = get_typesense_client()
    seen_sets: set[tuple[str, ...]] = set()
    synonym_groups: list[list[str]] = []

    for word, aliases in SEARCH_SYNONYMS.items():
        group = sorted({word, *aliases})
        key = tuple(group)
        if key not in seen_sets:
            seen_sets.add(key)
            synonym_groups.append(group)

    for word, aliases in BRAND_ALIASES.items():
        group = sorted({word, *aliases})
        key = tuple(group)
        if key not in seen_sets:
            seen_sets.add(key)
            synonym_groups.append(group)

    for idx, group in enumerate(synonym_groups):
        client.collections[COLLECTION_NAME].synonyms.upsert(
            f"syn-{idx}",
            {"synonyms": group},
        )


def ensure_collection(recreate: bool = False):
    client = get_typesense_client()
    if recreate:
        try:
            client.collections[COLLECTION_NAME].delete()
        except typesense.exceptions.ObjectNotFound:
            pass
    try:
        collection = client.collections[COLLECTION_NAME].retrieve()
    except typesense.exceptions.ObjectNotFound:
        collection = client.collections.create(_collection_schema())
    try:
        _sync_synonyms()
    except Exception:
        pass
    return collection


def get_index():
    """Backward-compatible alias used by manage.py."""
    return ensure_collection()


def _post_to_doc(post: Post) -> dict:
    doc = post.to_dict()
    doc["status"] = post.status
    if doc.get("price") is None:
        doc.pop("price", None)
    return doc


def index_post(post: Post):
    try:
        ensure_collection()
        get_typesense_client().collections[COLLECTION_NAME].documents.upsert(_post_to_doc(post))
    except Exception:
        pass


def upsert_published_rank_scores() -> int:
    posts = Post.query.filter_by(status="published").all()
    if not posts:
        return 0
    try:
        ensure_collection()
        docs = [_post_to_doc(post) for post in posts]
        get_typesense_client().collections[COLLECTION_NAME].documents.import_(
            docs,
            {"action": "upsert"},
        )
        return len(docs)
    except Exception:
        return 0


def reindex_published_posts() -> int:
    posts = Post.query.filter_by(status="published").all()
    try:
        ensure_collection(recreate=True)
        if not posts:
            return 0
        docs = [_post_to_doc(post) for post in posts]
        get_typesense_client().collections[COLLECTION_NAME].documents.import_(
            docs,
            {"action": "create"},
        )
        return len(docs)
    except Exception:
        return 0


def remove_post_from_index(post_id: str):
    try:
        get_typesense_client().collections[COLLECTION_NAME].documents[post_id].delete()
    except Exception:
        pass


def _build_filter(
    city: str | None,
    category: str | None,
    price_min: int | None,
    price_max: int | None,
    with_photo: bool,
    with_price: bool = False,
) -> str:
    parts = ["status:=published"]
    if city and city in CITIES:
        parts.append(f"city:={city}")
    if category and category in CATEGORIES:
        parts.append(f"category:={category}")
    if price_min is not None:
        parts.append(f"price:>={price_min}")
    if price_max is not None:
        parts.append(f"price:<={price_max}")
    if with_photo:
        parts.append("has_photo:=true")
    if with_price:
        parts.append("price:>0")
    return " && ".join(parts)


def _extract_highlight(hit: dict) -> dict:
    highlight = {}
    for item in hit.get("highlights", []):
        field = item.get("field")
        value = item.get("snippet") or item.get("value", "")
        if field and value:
            highlight[field] = sanitize_highlight(value)
    return highlight


def sanitize_highlight(value: str) -> Markup:
    """Allow only Typesense's simple mark tags in highlighted snippets."""
    import re

    parts = re.split(r"(</?mark>)", value)
    safe = []
    for part in parts:
        if part in ("<mark>", "</mark>"):
            safe.append(part)
        else:
            safe.append(str(escape(part)))
    return Markup("".join(safe))


def _build_search_query(query: str, expanded_terms: list[str] | None) -> str:
    if not query:
        return "*"
    terms = expanded_terms or [query]
    unique = []
    seen = set()
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return " ".join(unique) if unique else query


def _typesense_search(
    query: str,
    city: str | None,
    category: str | None,
    price_min: int | None,
    price_max: int | None,
    with_photo: bool,
    with_price: bool,
    sort: str,
    limit: int,
    offset: int,
    expanded_terms: list[str] | None = None,
) -> dict:
    ensure_collection()
    has_query = bool(query)
    use_rerank = uses_hybrid_ranking(sort) or (has_query and sort in {"price_asc", "price_desc"})
    if use_rerank:
        per_page = _candidate_limit(limit, offset)
        page = 1
    else:
        per_page = limit
        page = (offset // limit) + 1 if limit else 1

    params = {
        "q": _build_search_query(query, expanded_terms),
        "query_by": "title,body",
        "query_by_weights": "3,1",
        "num_typos": 2,
        "typo_tokens_threshold": 1,
        "prioritize_exact_match": True,
        "drop_tokens_threshold": 1,
        "filter_by": _build_filter(city, category, price_min, price_max, with_photo, with_price),
        "per_page": per_page,
        "page": page,
        "highlight_fields": "title,body",
        "highlight_full_fields": "title,body",
    }
    sort_by = _typesense_sort(sort, has_query)
    if sort_by:
        params["sort_by"] = sort_by
    return get_typesense_client().collections[COLLECTION_NAME].documents.search(params)


def _count_published_posts(
    query: str,
    city: str | None,
    category: str | None,
    price_min: int | None,
    price_max: int | None,
    with_photo: bool,
    with_price: bool = False,
) -> int:
    _, total = search_posts_fallback(
        query, city, category, price_min, price_max, with_photo, with_price, DEFAULT_SORT, limit=1, offset=0
    )
    return total


def _resolve_sort(sort: str, query: str) -> str:
    if sort in SORT_OPTIONS:
        return sort
    return DEFAULT_SEARCH_SORT if query else DEFAULT_SORT


def _rerank_sql_results(
    posts: list[Post],
    *,
    query: str,
    sort: str,
    price_min: int | None,
    price_max: int | None,
) -> list[dict]:
    mode = "search" if query else "feed"
    hits = [{"document": {"id": post.id}, "text_match": 0, "highlights": []} for post in posts]
    posts_map = {post.id: post for post in posts}
    return rerank_hits(
        hits,
        posts_map,
        query=query,
        mode=mode,
        sort=sort,
        price_min=price_min,
        price_max=price_max,
        extract_highlight=lambda _hit: {},
    )


def search_posts_fallback(
    query: str,
    city: str | None = None,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    sort: str = DEFAULT_SORT,
    limit: int = 20,
    offset: int = 0,
    expanded_terms: list[str] | None = None,
):
    sort = _resolve_sort(sort, query)

    q = _live_posts_query(Post.query.filter_by(status="published"))
    if city:
        q = q.filter_by(city=city)
    if category:
        q = q.filter_by(category=category)
    if price_min is not None:
        q = q.filter(Post.price >= price_min)
    if price_max is not None:
        q = q.filter(Post.price <= price_max)
    if with_photo:
        q = q.filter(Post.has_photo.is_(True))
    if with_price:
        q = q.filter(Post.price.isnot(None), Post.price > 0)
    if query:
        terms = expanded_terms or [query]
        clauses = []
        for term in terms:
            like = f"%{term}%"
            clauses.append(or_(Post.title.ilike(like), Post.body.ilike(like)))
        q = q.filter(or_(*clauses))

    total = q.count()
    if uses_hybrid_ranking(sort) or (query and sort in {"price_asc", "price_desc"}):
        candidate_limit = _candidate_limit(limit, offset)
        posts = q.limit(candidate_limit).all()
        ranked = _rerank_sql_results(
            posts,
            query=query,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
        )
        return ranked[offset : offset + limit], total

    q = _apply_sql_sort(q, sort)
    posts = q.offset(offset).limit(limit).all()
    return [{"post": p, "highlight": {}, "score": p.rank_score or 0} for p in posts], total


def search_posts(
    query: str,
    city: str | None = None,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    sort: str = DEFAULT_SORT,
    limit: int = 20,
    offset: int = 0,
    expanded_terms: list[str] | None = None,
):
    sort = _resolve_sort(sort, query)

    try:
        result = _typesense_search(
            query,
            city,
            category,
            price_min,
            price_max,
            with_photo,
            with_price,
            sort,
            limit,
            offset,
            expanded_terms=expanded_terms,
        )
        hits = result.get("hits", [])
        post_ids = [h["document"]["id"] for h in hits if h.get("document", {}).get("id")]
        posts_map = (
            {p.id: p for p in Post.query.filter(Post.id.in_(post_ids)).all()}
            if post_ids
            else {}
        )

        mode = "search" if query else "feed"
        results = rerank_hits(
            hits,
            posts_map,
            query=query,
            mode=mode,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
            extract_highlight=_extract_highlight,
        )

        if uses_hybrid_ranking(sort) or (query and sort in {"price_asc", "price_desc"}):
            results = results[offset : offset + limit]

        if not results:
            return search_posts_fallback(
                query,
                city,
                category,
                price_min,
                price_max,
                with_photo,
                with_price,
                sort,
                limit,
                offset,
                expanded_terms=expanded_terms,
            )

        total = _count_published_posts(query, city, category, price_min, price_max, with_photo, with_price)
        return results, total
    except Exception:
        return search_posts_fallback(
            query,
            city,
            category,
            price_min,
            price_max,
            with_photo,
            with_price,
            sort,
            limit,
            offset,
            expanded_terms=expanded_terms,
        )


def _posts_matching_parsed(
    text: str,
    *,
    city: str | None = None,
    category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    expanded_terms: list[str] | None = None,
):
    q = _live_posts_query(Post.query.filter_by(status="published"))
    if city:
        q = q.filter_by(city=city)
    if category:
        q = q.filter_by(category=category)
    if price_min is not None:
        q = q.filter(Post.price >= price_min)
    if price_max is not None:
        q = q.filter(Post.price <= price_max)
    if with_photo:
        q = q.filter(Post.has_photo.is_(True))
    if with_price:
        q = q.filter(Post.price.isnot(None), Post.price > 0)
    if text:
        terms = expanded_terms or [text]
        clauses = []
        for term in terms:
            like = f"%{term}%"
            clauses.append(or_(Post.title.ilike(like), Post.body.ilike(like)))
        q = q.filter(or_(*clauses))
    return q


def _best_price_threshold(prices: list[int]) -> int | None:
    if len(prices) < 2:
        return None
    for threshold in PRICE_SUGGEST_THRESHOLDS:
        below = sum(1 for price in prices if price <= threshold)
        above = sum(1 for price in prices if price > threshold)
        if below > 0 and above > 0:
            return threshold
    return None


def _refinement_suggestions(raw_query: str) -> list[str]:
    parsed = parse_search_query(raw_query)
    text = parsed["text"] or raw_query.strip()
    if len(text) < 2:
        return []

    base = _posts_matching_parsed(
        text,
        city=parsed["city"],
        category=parsed["category"],
        price_min=parsed["price_min"],
        price_max=parsed["price_max"],
        with_photo=parsed["with_photo"],
        expanded_terms=parsed.get("expanded_terms"),
    )
    if not base.limit(1).first():
        return []

    items = []
    query_label = raw_query.strip()
    if not parsed["with_photo"]:
        total = base.count()
        with_photo = base.filter(Post.has_photo.is_(True)).count()
        if 0 < with_photo < total:
            items.append(f"{query_label} с фото")

    if parsed["price_max"] is None:
        prices = [
            row[0]
            for row in base.with_entities(Post.price)
            .filter(Post.price.isnot(None))
            .limit(100)
            .all()
        ]
        threshold = _best_price_threshold(prices)
        if threshold is not None:
            items.append(f"{query_label} до {threshold}")

    return items


def _popular_suggestions(query: str) -> list[str]:
    query_norm = query.lower().strip()
    if len(query_norm) < 2:
        return []

    items = []
    for suggestion in POPULAR_SUGGESTIONS:
        suggestion_norm = suggestion.lower()
        if query_norm not in suggestion_norm and not suggestion_norm.startswith(query_norm):
            continue
        parsed = parse_search_query(suggestion)
        if _posts_matching_parsed(
            parsed["text"],
            city=parsed["city"],
            category=parsed["category"],
            price_min=parsed["price_min"],
            price_max=parsed["price_max"],
            with_photo=parsed["with_photo"],
            expanded_terms=parsed.get("expanded_terms"),
        ).limit(1).first():
            items.append(suggestion)
    return items


def suggest(query: str, limit: int = 5):
    if not query or len(query) < 2:
        return []

    titles: list[str] = []
    try:
        result = _typesense_search(
            query=query,
            city=None,
            category=None,
            price_min=None,
            price_max=None,
            with_photo=False,
            sort=DEFAULT_SEARCH_SORT,
            limit=limit,
            offset=0,
        )
        titles = [
            h["document"]["title"]
            for h in result.get("hits", [])
            if h.get("document", {}).get("title")
        ]
    except Exception:
        like = f"%{query}%"
        posts = (
            Post.query.filter(Post.status == "published", Post.title.ilike(like))
            .limit(limit)
            .all()
        )
        titles = [post.title for post in posts]

    items = list(
        dict.fromkeys(
            titles
            + smart_suggestions(query, limit=limit)
            + _refinement_suggestions(query)
            + _popular_suggestions(query)
        )
    )
    return items[:limit]
