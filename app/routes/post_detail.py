from urllib.parse import urlparse

from flask import render_template, request, url_for

from app.constants import CATEGORIES, CATEGORY_LABELS, CITIES
from app.services.posts import increment_views
from app.services.seo import post_json_ld, post_og_image, post_public_url, site_name
from app.utils.post_display import ordered_images


def render_gone_page():
    return render_template("errors/410.html"), 410


def build_show_context(post, *, owner_preview: bool = False, owner_token: str | None = None):
    referrer = request.referrer or ""
    parsed_referrer = urlparse(referrer)
    back_url = url_for("main.index")
    if referrer and parsed_referrer.netloc == request.host and parsed_referrer.path in ("", "/"):
        back_url = referrer

    canonical_url = post_public_url(post, external=True)
    og_image = post_og_image(post)
    og_description = (post.body or "")[:200].replace("\n", " ").strip()
    page_title = f"{post.title} — {site_name()}"
    json_ld = post_json_ld(post, canonical_url=canonical_url, image_url=og_image)

    return {
        "post": post,
        "gallery_images": ordered_images(post),
        "owner_preview": owner_preview,
        "owner_token": owner_token,
        "back_url": back_url,
        "cities": CITIES,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "og_image": og_image,
        "og_description": og_description,
        "page_title": page_title,
        "canonical_url": canonical_url,
        "json_ld": json_ld,
        "robots": "index, follow",
    }


def render_show_page(post):
    increment_views(post)
    return render_template("posts/show.html", **build_show_context(post, owner_preview=False))
