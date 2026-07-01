from __future__ import annotations

from urllib.parse import urlencode

from flask import current_app, request, url_for

from app.constants import CATEGORIES, CATEGORY_LABELS, CITIES
from app.routes.media import resolve_image_url
from app.services.storage import extract_s3_key


def site_name() -> str:
    return current_app.config.get("SITE_NAME", "Поискер")


def site_tagline() -> str:
    return current_app.config.get("SITE_TAGLINE", "Доска объявлений Чеченской Республики")


def site_description() -> str:
    return current_app.config.get(
        "SITE_DESCRIPTION",
        "Поискер — бесплатные объявления по Чеченской Республике. Без регистрации и SMS.",
    )


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
    if not post.images:
        return None
    first = post.images[0]
    resolved = resolve_image_url(first)
    if resolved.startswith("/static/"):
        return absolute_url(resolved)
    key = extract_s3_key(first)
    if key:
        return absolute_url(url_for("media.serve", key=key))
    if resolved.startswith("/"):
        return absolute_url(resolved)
    return None


def listing_seo_title(*, query: str = "", city: str = "", category: str = "") -> str:
    parts = []
    if query:
        parts.append(query)
    if category and category in CATEGORY_LABELS:
        parts.append(CATEGORY_LABELS[category])
    if city and city in CITIES:
        parts.append(CITIES[city])
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
    params = {}
    if ctx.get("query"):
        params["q"] = ctx["query"]
    if ctx.get("city"):
        params["city"] = ctx["city"]
    if ctx.get("category"):
        params["category"] = ctx["category"]
    if ctx.get("price_min"):
        params["price_min"] = ctx["price_min"]
    if ctx.get("price_max"):
        params["price_max"] = ctx["price_max"]
    if ctx.get("sort"):
        params["sort"] = ctx["sort"]
    if ctx.get("with_photo"):
        params["with_photo"] = "1"
    if ctx.get("with_price"):
        params["with_price"] = "1"
    page = ctx.get("page", 1) or 1
    if page > 1:
        params["page"] = page
    base = absolute_url("/")
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def city_category_path(city_slug: str, category_slug: str | None = None) -> str:
    if category_slug:
        return url_for("main.city_category_page", city_slug=city_slug, category_slug=category_slug)
    return url_for("main.city_page", city_slug=city_slug)


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
