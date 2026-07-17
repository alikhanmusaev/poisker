from urllib.parse import urlparse
import json

from django.conf import settings
from django.db.models import F
from django.urls import reverse
from django.utils.html import strip_tags

from listings.constants import CATEGORY_LABELS, CITIES
from listings.models import Post
from listings.services.seo_urls import post_public_url
from listings.utils.post_display import ordered_images


def increment_views(request, post: Post) -> bool:
    """Count at most once per browser session; never count the owner's own opens."""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False) and post.user_id == user.id:
        return False

    session = getattr(request, "session", None)
    if session is None:
        Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
        post.views = (post.views or 0) + 1
        return True

    key = "viewed_post_ids"
    post_id = str(post.pk)
    viewed = list(session.get(key) or [])
    if post_id in viewed:
        return False

    Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
    post.views = (post.views or 0) + 1
    viewed.append(post_id)
    # Cap list so the session cookie/store does not grow without bound.
    if len(viewed) > 200:
        viewed = viewed[-200:]
    session[key] = viewed
    session.modified = True
    return True


def build_show_context(request, post: Post) -> dict:
    referrer = request.META.get("HTTP_REFERER", "")
    back_url = reverse("core:index")
    if referrer:
        parsed = urlparse(referrer)
        host = request.get_host()
        if parsed.netloc == host and parsed.path in ("", "/"):
            back_url = referrer

    from bookmarks.services import is_post_bookmarked

    city_name = CITIES.get(post.city, post.city)
    category_name = CATEGORY_LABELS.get(post.category, post.category)
    body_plain = " ".join(strip_tags(post.body or "").split())
    snippet = body_plain[:160].rstrip()
    if len(body_plain) > 160:
        snippet = f"{snippet}…"
    if post.price is not None:
        price_bit = f"{post.price} ₽ · "
    else:
        price_bit = ""
    seo_description = f"{price_bit}{post.title} — {city_name}, {category_name}. {snippet}".strip()
    if len(seo_description) > 300:
        seo_description = seo_description[:297].rstrip() + "…"

    gallery = ordered_images(post)
    canonical_path = post_public_url(post)
    canonical_url = f"https://{settings.APP_DOMAIN}{canonical_path}"
    og_image = gallery[0] if gallery else f"https://{settings.APP_DOMAIN}/static/icons/icon-512.png"

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": post.title,
        "description": body_plain[:5000] if body_plain else post.title,
        "url": canonical_url,
        "category": category_name,
        "offers": {
            "@type": "Offer",
            "url": canonical_url,
            "availability": "https://schema.org/InStock",
            "priceCurrency": "RUB",
            "areaServed": city_name,
        },
    }
    if post.price is not None:
        json_ld["offers"]["price"] = str(post.price)
    if gallery:
        json_ld["image"] = gallery[:5]

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": f"https://{settings.APP_DOMAIN}/"},
            {
                "@type": "ListItem",
                "position": 2,
                "name": city_name,
                "item": f"https://{settings.APP_DOMAIN}/{post.city}/",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": category_name,
                "item": f"https://{settings.APP_DOMAIN}/{post.city}/{post.category}/",
            },
            {"@type": "ListItem", "position": 4, "name": post.title, "item": canonical_url},
        ],
    }

    return {
        "post": post,
        "gallery_images": gallery,
        "back_url": back_url,
        "category_labels": CATEGORY_LABELS,
        "cities": CITIES,
        "is_bookmarked": is_post_bookmarked(request.user, post),
        "seo_title": f"{post.title} — {settings.SITE_NAME}",
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "og_image_url": og_image,
        "json_ld_json": json.dumps(json_ld, ensure_ascii=False),
        "breadcrumb_ld_json": json.dumps(breadcrumb_ld, ensure_ascii=False),
        "robots_noindex": post.status != "published",
    }
