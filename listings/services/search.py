"""Typesense search with Django ORM fallback."""

import logging
import typesense
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe

from listings.constants import (
    BRAND_ALIASES,
    CATEGORIES,
    CITIES,
    ALLOWED_SORTS,
    DEFAULT_SEARCH_SORT,
    DEFAULT_SORT,
    POPULAR_SUGGESTIONS,
    SEARCH_SYNONYMS,
)
from listings.models import Post
from listings.services.search_ranking import rerank_hits, uses_hybrid_ranking
from listings.services.smart_query import parse_search_query, smart_suggestions

COLLECTION_NAME = "posts"
logger = logging.getLogger(__name__)
CANDIDATE_MIN = 60
CANDIDATE_MAX = 250
_collection_ready = False


def _live_posts_qs():
    return (
        Post.objects.filter(status="published", expires_at__gte=timezone.now())
        .select_related("user", "settlement", "settlement__region")
    )


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
            {"name": "expires_at", "type": "int64", "optional": True},
            {"name": "paid_boost", "type": "float", "optional": True},
        ],
        "default_sorting_field": "rank_score",
        "token_separators": ["-", "_"],
    }


def get_typesense_client():
    url = urlparse(settings.TYPESENSE_URL)
    return typesense.Client(
        {
            "nodes": [{"host": url.hostname or "localhost", "port": str(url.port or 8108), "protocol": url.scheme or "http"}],
            "api_key": settings.TYPESENSE_API_KEY,
            "connection_timeout_seconds": 5,
        }
    )


def _sync_synonyms(client):
    seen: set[tuple[str, ...]] = set()
    groups: list[list[str]] = []
    for mapping in (SEARCH_SYNONYMS, BRAND_ALIASES):
        for word, aliases in mapping.items():
            group = sorted({word, *aliases})
            key = tuple(group)
            if key not in seen:
                seen.add(key)
                groups.append(group)
    for idx, group in enumerate(groups):
        client.collections[COLLECTION_NAME].synonyms.upsert(f"syn-{idx}", {"synonyms": group})


def ensure_collection(recreate: bool = False, *, sync_synonyms: bool = True):
    global _collection_ready
    client = get_typesense_client()
    if recreate:
        try:
            client.collections[COLLECTION_NAME].delete()
        except typesense.exceptions.ObjectNotFound:
            pass
        _collection_ready = False
    try:
        collection = client.collections[COLLECTION_NAME].retrieve()
        field_names = {f.get("name") for f in collection.get("fields", [])}
        if "expires_at" not in field_names:
            client.collections[COLLECTION_NAME].delete()
            collection = client.collections.create(_collection_schema())
            _collection_ready = False
    except typesense.exceptions.ObjectNotFound:
        collection = client.collections.create(_collection_schema())
        _collection_ready = False
    if sync_synonyms and not _collection_ready:
        try:
            _sync_synonyms(client)
            _collection_ready = True
        except Exception:
            logger.exception("Failed to sync Typesense synonyms")
            _collection_ready = False
    return collection


def ensure_collection_exists():
    """Fast path for search — skip synonym sync and avoid retrieve on every request."""
    global _collection_ready
    if _collection_ready:
        return True
    client = get_typesense_client()
    try:
        client.collections[COLLECTION_NAME].retrieve()
        _collection_ready = True
        return True
    except typesense.exceptions.ObjectNotFound:
        return ensure_collection(sync_synonyms=True)


def _post_to_doc(post: Post) -> dict:
    doc = post.to_search_doc()
    if doc.get("price") is None:
        doc.pop("price", None)
    return doc


def index_post(post: Post):
    try:
        ensure_collection_exists()
        get_typesense_client().collections[COLLECTION_NAME].documents.upsert(_post_to_doc(post))
    except Exception:
        logger.exception("Failed to index post %s", post.pk)


def upsert_posts_to_index(posts) -> int:
    """Bulk upsert without per-row ensure_collection/synonym sync."""
    posts = list(posts)
    if not posts:
        return 0
    try:
        ensure_collection_exists()
        docs = [_post_to_doc(p) for p in posts]
        get_typesense_client().collections[COLLECTION_NAME].documents.import_(
            docs, {"action": "upsert"}
        )
        return len(docs)
    except Exception:
        logger.exception("Failed to bulk upsert %s posts", len(posts))
        return 0


def remove_post_from_index(post_id: str):
    try:
        get_typesense_client().collections[COLLECTION_NAME].documents[str(post_id)].delete()
    except Exception as exc:
        if getattr(exc, "http_status", None) == 404 or "Could not find a document" in str(exc):
            return
        logger.exception("Failed to remove post %s from index", post_id)


def reindex_published_posts() -> int:
    posts = list(_live_posts_qs())
    try:
        ensure_collection(recreate=True)
        if not posts:
            return 0
        docs = [_post_to_doc(p) for p in posts]
        get_typesense_client().collections[COLLECTION_NAME].documents.import_(docs, {"action": "create"})
        return len(docs)
    except Exception:
        logger.exception("Failed to reindex published posts")
        return 0


def upsert_published_rank_scores() -> int:
    posts = list(_live_posts_qs())
    if not posts:
        return 0
    try:
        ensure_collection()
        docs = [_post_to_doc(p) for p in posts]
        get_typesense_client().collections[COLLECTION_NAME].documents.import_(docs, {"action": "upsert"})
        return len(docs)
    except Exception:
        logger.exception("Failed to upsert rank scores")
        return 0


def _build_filter(city, category, price_min, price_max, with_photo, with_price=False) -> str:
    now_ts = int(timezone.now().timestamp())
    parts = ["status:=published", f"expires_at:>={now_ts}"]
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


def sanitize_highlight(value: str):
    import re

    parts = re.split(r"(</?mark>)", value)
    safe = []
    for part in parts:
        if part in ("<mark>", "</mark>"):
            safe.append(part)
        else:
            safe.append(str(escape(part)))
    return mark_safe("".join(safe))


def _extract_highlight(hit: dict) -> dict:
    highlight = {}
    for item in hit.get("highlights", []):
        field = item.get("field")
        value = item.get("snippet") or item.get("value", "")
        if field and value:
            highlight[field] = sanitize_highlight(value)
    return highlight


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


def _candidate_limit(limit: int, offset: int) -> int:
    return min(max(CANDIDATE_MIN, (offset + limit) * 3), CANDIDATE_MAX)


def _build_search_query(query: str, expanded_terms: list[str] | None) -> str:
    if not query:
        return "*"
    unique = []
    seen = set()
    for term in expanded_terms or [query]:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return " ".join(unique) if unique else query


def _typesense_search(query, city, category, price_min, price_max, with_photo, with_price, sort, limit, offset, expanded_terms=None):
    ensure_collection_exists()
    has_query = bool(query)
    # Empty browse feed: trust Typesense rank_score sort — no 3× candidate over-fetch.
    use_rerank = bool(has_query) and (
        uses_hybrid_ranking(sort) or sort in {"price_asc", "price_desc"}
    )
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
        "filter_by": _build_filter(city, category, price_min, price_max, with_photo, with_price),
        "per_page": per_page,
        "page": page,
    }
    if has_query:
        params["num_typos"] = 2
        params["highlight_fields"] = "title,body"
    else:
        params["num_typos"] = 0
    sort_by = _typesense_sort(sort, has_query)
    if sort_by:
        params["sort_by"] = sort_by
    return get_typesense_client().collections[COLLECTION_NAME].documents.search(params)


def _resolve_sort(sort: str, query: str) -> str:
    if sort in ALLOWED_SORTS:
        return sort
    return DEFAULT_SEARCH_SORT if query else DEFAULT_SORT


def _apply_text_filter(qs, query: str, expanded_terms: list[str] | None):
    if not query:
        return qs
    clause = Q()
    for term in expanded_terms or [query]:
        clause |= Q(title__icontains=term) | Q(body__icontains=term)
    return qs.filter(clause)


def _apply_filters(
    qs,
    city,
    category,
    price_min,
    price_max,
    with_photo,
    with_price,
    settlement_id=None,
    region_id=None,
):
    if settlement_id:
        settlement_slug = (
            qs.model._meta.get_field("settlement")
            .related_model.objects.filter(pk=settlement_id)
            .values_list("slug", flat=True)
            .first()
        )
        settlement_filter = Q(settlement_id=settlement_id)
        if settlement_slug:
            settlement_filter |= Q(city=settlement_slug)
        qs = qs.filter(settlement_filter)
    elif city:
        qs = qs.filter(city=city)
    if region_id:
        qs = qs.filter(settlement__region_id=region_id)
    if category:
        qs = qs.filter(category=category)
    if price_min is not None:
        qs = qs.filter(price__gte=price_min)
    if price_max is not None:
        qs = qs.filter(price__lte=price_max)
    if with_photo:
        qs = qs.filter(has_photo=True)
    if with_price:
        qs = qs.filter(price__isnull=False, price__gt=0)
    return qs


def _apply_sql_sort(qs, sort: str):
    if sort == "price_asc":
        return qs.order_by("price", "-rank_score", "-created_at")
    if sort == "price_desc":
        return qs.order_by("-price", "-rank_score", "-created_at")
    if sort == "date_desc":
        return qs.order_by("-created_at")
    return qs.order_by("-rank_score", "-created_at")


def search_posts_fallback(query, city=None, category=None, price_min=None, price_max=None, with_photo=False, with_price=False, sort=DEFAULT_SORT, limit=20, offset=0, expanded_terms=None, boost_city=None, settlement_id=None, region_id=None):
    sort = _resolve_sort(sort, query)
    qs = _apply_filters(
        _live_posts_qs(), city, category, price_min, price_max, with_photo, with_price,
        settlement_id=settlement_id, region_id=region_id,
    )
    qs = _apply_text_filter(qs, query, expanded_terms)
    total = qs.count()

    if query and (uses_hybrid_ranking(sort) or sort in {"price_asc", "price_desc"}):
        posts = list(qs[: _candidate_limit(limit, offset)])
        hits = [{"document": {"id": str(p.pk)}, "text_match": 0, "highlights": []} for p in posts]
        posts_map = {str(p.pk): p for p in posts}
        ranked = rerank_hits(
            hits,
            posts_map,
            query=query,
            mode="search" if query else "feed",
            sort=sort,
            price_min=price_min,
            price_max=price_max,
            boost_city=boost_city,
            extract_highlight=lambda _h: {},
        )
        return ranked[offset : offset + limit], total

    posts = list(_apply_sql_sort(qs, sort)[offset : offset + limit])
    return [{"post": p, "highlight": {}, "score": p.rank_score or 0} for p in posts], total


def _hydrate_posts_map(post_ids: list[str]) -> dict:
    if not post_ids:
        return {}
    # Fields needed for feed cards, SEO URLs, and light seller diversity.
    qs = _live_posts_qs().filter(pk__in=post_ids).only(
        "id",
        "title",
        "slug",
        "price",
        "condition",
        "city",
        "category",
        "images",
        "cover_index",
        "user_id",
        "rank_score",
        "created_at",
        "status",
        "expires_at",
    )
    return {str(p.pk): p for p in qs}


def _results_from_typesense_order(hits, posts_map, *, diversify: bool = False):
    from listings.services.search_ranking import diversify_by_seller

    results = []
    for hit in hits:
        doc = hit.get("document") or {}
        post = posts_map.get(doc.get("id"))
        if not post:
            continue
        results.append(
            {
                "post": post,
                "highlight": {},
                "score": post.rank_score or 0,
            }
        )
    if diversify:
        results = diversify_by_seller(results)
    return results


def search_posts(query, city=None, category=None, price_min=None, price_max=None, with_photo=False, with_price=False, sort=DEFAULT_SORT, limit=20, offset=0, expanded_terms=None, boost_city=None, settlement_id=None, region_id=None):
    sort = _resolve_sort(sort, query)
    # The current Typesense collection has legacy city facets only. Geography
    # filters must include unmigrated city-slug rows, so apply them in SQL.
    if settlement_id or region_id:
        return search_posts_fallback(
            query, city, category, price_min, price_max, with_photo, with_price,
            sort, limit, offset, expanded_terms, boost_city=boost_city,
            settlement_id=settlement_id, region_id=region_id,
        )
    use_rerank = bool(query) and (
        uses_hybrid_ranking(sort) or sort in {"price_asc", "price_desc"}
    )
    # Empty browse: keep Typesense order (optional light seller diversity for default rank).
    trust_typesense_order = not query
    try:
        result = _typesense_search(query, city, category, price_min, price_max, with_photo, with_price, sort, limit, offset, expanded_terms)
        hits = result.get("hits", [])
        post_ids = [h["document"]["id"] for h in hits if h.get("document", {}).get("id")]
        posts_map = _hydrate_posts_map(post_ids)
        if trust_typesense_order:
            results = _results_from_typesense_order(
                hits,
                posts_map,
                diversify=(sort == "rank"),
            )
        else:
            mode = "search" if query else "feed"
            results = rerank_hits(
                hits,
                posts_map,
                query=query,
                mode=mode,
                sort=sort,
                price_min=price_min,
                price_max=price_max,
                boost_city=boost_city,
                extract_highlight=_extract_highlight,
            )
            if use_rerank:
                results = results[offset : offset + limit]
        if not results and hits:
            return search_posts_fallback(
                query, city, category, price_min, price_max, with_photo, with_price,
                sort, limit, offset, expanded_terms, boost_city=boost_city,
            )
        total = int(result.get("found") or 0)
        return results, total
    except Exception:
        logger.exception("Typesense search failed, using SQL fallback")
        return search_posts_fallback(
            query, city, category, price_min, price_max, with_photo, with_price,
            sort, limit, offset, expanded_terms, boost_city=boost_city,
        )


def suggest(query: str, limit: int = 5):
    if not query or len(query) < 2:
        return []
    titles: list[str] = []
    try:
        result = _typesense_search(query, None, None, None, None, False, False, DEFAULT_SEARCH_SORT, limit, 0)
        titles = [h["document"]["title"] for h in result.get("hits", []) if h.get("document", {}).get("title")]
    except Exception:
        titles = list(_live_posts_qs().filter(title__icontains=query).values_list("title", flat=True)[:limit])
    items = list(dict.fromkeys(titles + smart_suggestions(query, limit=limit)))
    return items[:limit]
