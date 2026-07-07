from __future__ import annotations

from urllib.parse import urlencode

from flask import current_app, request, url_for

from app.constants import CATEGORIES, CATEGORY_LABELS, CITIES, CITY_LOCATIVE, DEFAULT_SEARCH_SORT, DEFAULT_SORT
from app.routes.media import resolve_image_url
from app.utils.post_display import cover_image, ordered_images
from app.services.storage import extract_s3_key


def site_name() -> str:
    return current_app.config.get("SITE_NAME", "Поискер")


def site_tagline() -> str:
    return current_app.config.get("SITE_TAGLINE", "Доска объявлений Чеченской Республики")


def site_description() -> str:
    return current_app.config.get(
        "SITE_DESCRIPTION",
        "Поискер — бесплатные объявления по Чеченской Республике. Без регистрации и смс.",
    )


def post_image_alt(title: str, index: int = 1, total: int = 1) -> str:
    """Accessible alt text for listing and detail images."""
    clean = " ".join(str(title or "Объявление").split())
    if total > 1:
        return f"{clean} — фото {index} из {total}"
    return f"{clean} — фото"


def listing_og_image() -> str:
    return absolute_url("/static/icons/icon-512.png")


def site_json_ld() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name(),
        "url": absolute_url("/"),
        "description": site_description(),
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": absolute_url("/?q={search_term_string}"),
            },
            "query-input": "required name=search_term_string",
        },
    }


def site_base_url() -> str:
    domain = (current_app.config.get("APP_DOMAIN") or request.host or "poisker.ru").strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        return domain.rstrip("/")
    scheme = "https"
    if domain.startswith("localhost") or domain.startswith("127.0.0.1"):
        scheme = request.scheme
    return f"{scheme}://{domain}"


def post_public_path(post) -> str:
    slug = getattr(post, "slug", None)
    city = getattr(post, "city", None)
    category = getattr(post, "category", None)
    if slug and city in CITIES and category in CATEGORIES:
        return url_for(
            "main.post_public",
            city_slug=city,
            category_slug=category,
            slug=slug,
        )
    if slug:
        return url_for("main.post_public_legacy", slug=slug)
    return url_for("posts.show", post_id=post.id)


def post_public_url(post, *, external: bool = False) -> str:
    return site_base_url() + post_public_path(post) if external else post_public_path(post)


def absolute_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = site_base_url()
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def post_og_image(post) -> str | None:
    first = cover_image(post)
    if not first:
        return None
    resolved = resolve_image_url(first)
    if resolved.startswith("/static/"):
        return absolute_url(resolved)
    key = extract_s3_key(first)
    if key:
        return absolute_url(url_for("media.serve", key=key))
    if resolved.startswith("/"):
        return absolute_url(resolved)
    return None


def city_locative(city_slug: str) -> str:
    return CITY_LOCATIVE.get(city_slug, CITIES.get(city_slug, city_slug))


def listing_seo_title(*, query: str = "", city: str = "", category: str = "") -> str:
    if city and city in CITIES:
        loc = city_locative(city)
        if category and category in CATEGORY_LABELS:
            return f"{CATEGORY_LABELS[category]} в {loc} — {site_name()}"
        return f"Объявления в {loc} — {site_name()}"
    if category and category in CATEGORY_LABELS:
        return f"{CATEGORY_LABELS[category]} — {site_name()}"
    parts = []
    if query:
        parts.append(query)
    if category and category in CATEGORY_LABELS:
        parts.append(CATEGORY_LABELS[category])
    if parts:
        return f"{' '.join(parts)} — {site_name()}"
    return f"{site_name()} — {site_tagline()}"


def listing_seo_description(*, query: str = "", city: str = "", category: str = "") -> str:
    bits = [site_description()]
    if city and city in CITIES:
        bits.append(f"Город: {CITIES[city]}.")
    if category and category in CATEGORY_LABELS:
        bits.append(f"Категория: {CATEGORY_LABELS[category]}.")
    if query:
        bits.append(f"Поиск: {query}.")
    return " ".join(bits)


def listing_canonical_url(**ctx) -> str:
    city = ctx.get("city") or ""
    category = ctx.get("category") or ""
    page = ctx.get("page", 1) or 1
    fixed_city = ctx.get("fixed_city")
    fixed_category = ctx.get("fixed_category")
    has_extra = any(
        [
            ctx.get("query"),
            ctx.get("price_min"),
            ctx.get("price_max"),
            ctx.get("with_photo"),
            ctx.get("with_price"),
            page > 1,
        ]
    )
    if not has_extra:
        if city and category and city in CITIES and category in CATEGORIES:
            return absolute_url(city_category_path(city, category))
        if city and city in CITIES:
            return absolute_url(city_category_path(city))
        if category and category in CATEGORIES:
            return absolute_url(category_path(category))

    if city and category and city in CITIES and category in CATEGORIES:
        base_path = city_category_path(city, category)
    elif city and city in CITIES:
        base_path = city_category_path(city)
    elif category and category in CATEGORIES:
        base_path = category_path(category)
    else:
        base_path = "/"

    params = {}
    if ctx.get("query"):
        params["q"] = ctx["query"]
    if category and not fixed_category:
        params["category"] = category
    if city and not fixed_city:
        params["city"] = city
    if ctx.get("price_min"):
        params["price_min"] = ctx["price_min"]
    if ctx.get("price_max"):
        params["price_max"] = ctx["price_max"]
    if ctx.get("with_photo"):
        params["with_photo"] = 1
    if ctx.get("with_price"):
        params["with_price"] = 1
    if ctx.get("sort"):
        params["sort"] = ctx["sort"]
    if page > 1:
        params["page"] = page
    base = absolute_url(base_path)
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def city_category_path(city_slug: str, category_slug: str | None = None) -> str:
    if category_slug:
        return f"/{city_slug}/{category_slug}/"
    return f"/{city_slug}/"


def category_path(category_slug: str) -> str:
    return f"/{category_slug}/"


def listing_should_noindex(
    *,
    page: int,
    search_text: str = "",
    query: str = "",
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    sort: str = "",
) -> bool:
    """Filtered/paginated listing variants should not compete in search index."""
    if page > 1:
        return True
    if (search_text or query.strip()):
        return True
    if price_min is not None or price_max is not None:
        return True
    if with_photo or with_price:
        return True
    default_sort = DEFAULT_SEARCH_SORT if (search_text or query.strip()) else DEFAULT_SORT
    if sort and sort != default_sort:
        return True
    return False


def listing_page_url(
    listing_path: str,
    *,
    page: int = 1,
    query: str = "",
    city: str = "",
    category: str = "",
    fixed_city: str | None = None,
    fixed_category: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    with_photo: bool = False,
    with_price: bool = False,
    sort: str = "",
) -> str:
    """Build a listing URL that preserves path-based city/category and query filters."""
    params: dict[str, str | int] = {}
    if query:
        params["q"] = query
    if category and not fixed_category:
        params["category"] = category
    if city and not fixed_city:
        params["city"] = city
    if price_min is not None and price_min != "":
        params["price_min"] = price_min
    if price_max is not None and price_max != "":
        params["price_max"] = price_max
    if with_photo:
        params["with_photo"] = 1
    if with_price:
        params["with_price"] = 1
    if sort:
        params["sort"] = sort
    if page > 1:
        params["page"] = page
    if not params:
        return listing_path
    return f"{listing_path}?{urlencode(params)}"


def post_json_ld(post, *, canonical_url: str, image_url: str | None = None) -> dict:
    city_name = CITIES.get(post.city, post.city)
    category_name = CATEGORY_LABELS.get(post.category, post.category)
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": site_name(),
                        "item": absolute_url("/"),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": city_name,
                        "item": absolute_url(city_category_path(post.city)),
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": category_name,
                        "item": absolute_url(city_category_path(post.city, post.category)),
                    },
                    {
                        "@type": "ListItem",
                        "position": 4,
                        "name": post.title,
                        "item": canonical_url,
                    },
                ],
            },
            {
                "@type": "Product",
                "name": post.title,
                "description": (post.body or "")[:500],
                "category": category_name,
                "image": image_url or "",
                "offers": {
                    "@type": "Offer",
                    "url": canonical_url,
                    "priceCurrency": "RUB",
                    "availability": "https://schema.org/InStock",
                    **(
                        {"price": str(post.price)}
                        if post.price is not None
                        else {}
                    ),
                },
            },
        ],
    }
    return data
