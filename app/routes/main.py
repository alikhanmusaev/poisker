from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for

from app.constants import CATEGORIES, CITIES, DEFAULT_SEARCH_SORT, DEFAULT_SORT, SORT_OPTIONS
from app.extensions import limiter
from app.models import Post, utcnow
from app.routes.post_detail import render_show_page
from app.services.posts import get_published_post_by_slug
from app.services.search import search_posts, suggest
from app.services.seo import (
    absolute_url,
    city_category_path,
    listing_canonical_url,
    listing_seo_description,
    listing_seo_title,
    post_public_url,
)
from app.services.smart_query import parse_search_query

bp = Blueprint("main", __name__)

PER_PAGE = 20


def _normalize_price(value: int | None) -> int | None:
    if value is None or value < 0:
        return None
    return value


def _listing_context():
    query = request.args.get("q", "").strip()
    parsed = parse_search_query(query)
    city = request.args.get("city", "") or parsed["city"] or ""
    category = request.args.get("category", "") or parsed["category"] or ""
    price_min = _normalize_price(request.args.get("price_min", type=int) or parsed["price_min"])
    price_max = _normalize_price(request.args.get("price_max", type=int) or parsed["price_max"])
    if price_min is not None and price_max is not None and price_min > price_max:
        price_min, price_max = price_max, price_min
    with_photo = request.args.get("with_photo") == "1" or parsed["with_photo"]
    with_price = request.args.get("with_price") == "1" or parsed.get("with_price", False)
    sort = request.args.get("sort", "")
    if sort not in SORT_OPTIONS:
        sort = DEFAULT_SEARCH_SORT if parsed["text"] else DEFAULT_SORT
    page = max(request.args.get("page", 1, type=int), 1)
    offset = (page - 1) * PER_PAGE

    results, total = search_posts(
        query=parsed["text"],
        city=city or None,
        category=category or None,
        price_min=price_min,
        price_max=price_max,
        with_photo=with_photo,
        with_price=with_price,
        sort=sort,
        limit=PER_PAGE,
        offset=offset,
        expanded_terms=parsed.get("expanded_terms"),
    )
    has_next = page * PER_PAGE < total

    return {
        "query": query,
        "search_text": parsed["text"],
        "city": city,
        "category": category,
        "price_min": price_min,
        "price_max": price_max,
        "with_photo": with_photo,
        "with_price": with_price,
        "sort": sort,
        "page": page,
        "results": results,
        "total": total,
        "has_next": has_next,
        "cities": CITIES,
        "categories": CATEGORIES,
        "sort_options": SORT_OPTIONS,
        "seo_title": listing_seo_title(query=parsed["text"], city=city, category=category),
        "seo_description": listing_seo_description(
            query=parsed["text"], city=city, category=category
        ),
        "canonical_url": listing_canonical_url(
            query=query,
            city=city,
            category=category,
            price_min=price_min,
            price_max=price_max,
            with_photo=with_photo,
            with_price=with_price,
            sort=sort,
            page=page,
        ),
    }


@bp.route("/obyavlenie/<city_slug>/<category_slug>/<slug>")
@limiter.limit("120 per minute")
def post_public(city_slug, category_slug, slug):
    post = get_published_post_by_slug(slug)
    if not post:
        from flask import render_template

        return render_template("errors/404.html"), 404
    if city_slug != post.city or category_slug != post.category:
        return redirect(post_public_url(post), code=301)
    return render_show_page(post)


@bp.route("/obyavlenie/<slug>")
@limiter.limit("120 per minute")
def post_public_legacy(slug):
    post = get_published_post_by_slug(slug)
    if not post:
        from flask import render_template

        return render_template("errors/404.html"), 404
    return redirect(post_public_url(post), code=301)


@bp.route("/health")
def health():
    from sqlalchemy import text

    from app.extensions import db

    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok"), 200
    except Exception:
        return jsonify(status="error"), 503


@bp.route("/robots.txt")
def robots_txt():
    return (
        render_template("seo/robots.txt", sitemap_url=absolute_url("/sitemap.xml")),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@bp.route("/sitemap.xml")
def sitemap_xml():
    urls = [{"loc": absolute_url("/")}]
    for city_slug in CITIES:
        urls.append({"loc": absolute_url(city_category_path(city_slug))})
    for category_slug in CATEGORIES:
        urls.append({"loc": absolute_url(url_for("main.index", category=category_slug))})
        for city_slug in CITIES:
            urls.append(
                {
                    "loc": absolute_url(
                        url_for("main.city_category_page", city_slug=city_slug, category_slug=category_slug)
                    )
                }
            )

    posts = (
        Post.query.filter_by(status="published")
        .filter(Post.slug.isnot(None))
        .filter(Post.expires_at >= utcnow())
        .order_by(Post.created_at.desc())
        .limit(2000)
        .all()
    )
    for post in posts:
        urls.append(
            {
                "loc": post_public_url(post, external=True),
                "lastmod": post.created_at.strftime("%Y-%m-%d") if post.created_at else None,
            }
        )

    return (
        render_template("seo/sitemap.xml", urls=urls),
        200,
        {"Content-Type": "application/xml; charset=utf-8"},
    )


@bp.route("/")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def index():
    ctx = _listing_context()
    if request.headers.get("HX-Request"):
        if ctx["page"] > 1:
            return render_template("partials/post_list_more.html", **ctx)
        return render_template("partials/feed_panel.html", **ctx)
    return render_template("index.html", **ctx)


@bp.route("/suggest")
@limiter.limit(lambda: current_app.config["RATELIMIT_SUGGEST"])
def suggest_view():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        if request.headers.get("HX-Request"):
            return ""
        return {"suggestions": []}
    items = suggest(query)
    if request.headers.get("HX-Request"):
        return render_template("partials/suggest.html", items=items, query=query)
    return {"suggestions": items}


@bp.route("/gorod/<city_slug>")
def city_page(city_slug):
    if city_slug not in CITIES:
        return render_template("errors/404.html"), 404
    return redirect(url_for("main.index", city=city_slug, **request.args.to_dict()))


@bp.route("/gorod/<city_slug>/<category_slug>")
def city_category_page(city_slug, category_slug):
    if city_slug not in CITIES or category_slug not in CATEGORIES:
        return render_template("errors/404.html"), 404
    return redirect(
        url_for(
            "main.index",
            city=city_slug,
            category=category_slug,
            **{k: v for k, v in request.args.to_dict().items() if k != "category"},
        )
    )


@bp.route("/offline")
def offline():
    return render_template("offline.html")


@bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.route("/terms")
def terms():
    return render_template("terms.html")


@bp.route("/guidelines")
def guidelines():
    return render_template("guidelines.html")


@bp.route("/sw.js")
def service_worker():
    return send_from_directory(
        current_app.static_folder,
        "sw.js",
        mimetype="application/javascript",
    )


@bp.route("/.well-known/assetlinks.json")
def assetlinks():
    package = current_app.config.get("ANDROID_PACKAGE_NAME", "")
    fingerprints = current_app.config.get("ANDROID_SHA256_FINGERPRINTS", [])
    if not package or not fingerprints:
        return jsonify([])
    return jsonify(
        [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    )
