from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template, request, url_for
from app.constants import CATEGORIES, CITIES, DEFAULT_SEARCH_SORT, DEFAULT_SORT, RESERVED_SLUGS, SORT_OPTIONS
from app.extensions import limiter
from app.models import Post, utcnow
from app.routes.post_detail import render_show_page
from app.services.posts import get_published_post_by_slug, resolve_public_slug_view
from app.services.search import search_posts, suggest
from app.services.seo import (
    absolute_url,
    category_path,
    city_category_path,
    listing_canonical_url,
    listing_seo_description,
    listing_seo_title,
    listing_should_noindex,
    listing_og_image,
    post_public_url,
    site_json_ld,
)
from app.services.smart_query import parse_search_query

bp = Blueprint("main", __name__)

PER_PAGE = 20


def register_listing_converters(app) -> None:
    from werkzeug.exceptions import NotFound
    from werkzeug.routing import BaseConverter

    class ListingSlugConverter(BaseConverter):
        regex = r"[a-z0-9\.\-]+"

        def to_python(self, value):
            if value in RESERVED_SLUGS:
                raise NotFound()
            if value in CATEGORIES or value in CITIES:
                return value
            raise NotFound()

        def to_url(self, value):
            return value

    class ListingCityConverter(BaseConverter):
        regex = r"[a-z0-9\-]+"

        def to_python(self, value):
            if value in RESERVED_SLUGS or value not in CITIES:
                raise NotFound()
            return value

        def to_url(self, value):
            return value

    class ListingCategoryConverter(BaseConverter):
        regex = r"[a-z0-9\-]+"

        def to_python(self, value):
            if value in RESERVED_SLUGS or value not in CATEGORIES:
                raise NotFound()
            return value

        def to_url(self, value):
            return value

    app.url_map.converters["listing_slug"] = ListingSlugConverter
    app.url_map.converters["listing_city"] = ListingCityConverter
    app.url_map.converters["listing_category"] = ListingCategoryConverter


def _flag_enabled(name: str) -> bool:
    return request.args.get(name, "").lower() in ("1", "true", "yes", "on")


def _normalize_price(value: int | None) -> int | None:
    if value is None or value < 0:
        return None
    return value


def _listing_context(*, fixed_city: str | None = None, fixed_category: str | None = None):
    query = request.args.get("q", "").strip()
    parsed = parse_search_query(query)
    city = fixed_city or ""
    category = fixed_category or request.args.get("category", "") or parsed["category"] or ""
    price_min = _normalize_price(request.args.get("price_min", type=int) or parsed["price_min"])
    price_max = _normalize_price(request.args.get("price_max", type=int) or parsed["price_max"])
    if price_min is not None and price_max is not None and price_min > price_max:
        price_min, price_max = price_max, price_min
    with_photo = _flag_enabled("with_photo")
    with_price = _flag_enabled("with_price")
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

    robots_noindex = listing_should_noindex(
        page=page,
        search_text=parsed["text"],
        query=query,
        price_min=price_min,
        price_max=price_max,
        with_photo=with_photo,
        with_price=with_price,
        sort=sort,
    )

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
            fixed_city=fixed_city,
            fixed_category=fixed_category,
        ),
        "listing_path": request.path,
        "fixed_city": fixed_city,
        "fixed_category": fixed_category,
        "robots_noindex": robots_noindex,
        "listing_og_image": listing_og_image() if not robots_noindex else None,
        "json_ld": site_json_ld() if request.path == "/" and not robots_noindex else None,
    }


def _redirect_preserve_query(target_path: str, *, drop_params: set[str] | None = None):
    drop_params = drop_params or set()
    if not request.args:
        return redirect(target_path, code=301)
    params: list[tuple[str, str]] = []
    for key, values in request.args.lists():
        if key in drop_params:
            continue
        for value in values:
            params.append((key, value))
    if not params:
        return redirect(target_path, code=301)
    return redirect(f"{target_path}?{urlencode(params)}", code=301)


def _render_listing(**kwargs):
    ctx = _listing_context(**kwargs)
    if request.headers.get("HX-Request"):
        if ctx["page"] > 1:
            return render_template("partials/post_list_more.html", **ctx)
        return render_template("partials/feed_panel.html", **ctx)
    return render_template("index.html", **ctx)


@bp.route("/obyavlenie/<city_slug>/<category_slug>/<slug>")
@limiter.limit("120 per minute")
def post_public(city_slug, category_slug, slug):
    from flask import render_template

    from app.routes.post_detail import build_show_context, render_gone_page, render_show_page

    token = request.args.get("token", "")
    action, post = resolve_public_slug_view(
        slug,
        city_slug=city_slug,
        category_slug=category_slug,
        token=token or None,
    )
    if action == "not_found":
        return render_template("errors/404.html"), 404
    if action == "gone":
        return render_gone_page()
    if action == "redirect":
        return redirect(post_public_url(post), code=301)
    if action == "owner_preview":
        ctx = build_show_context(post, owner_preview=True, owner_token=token or None)
        ctx["robots"] = "noindex, nofollow"
        return render_template("posts/show.html", **ctx)
    return render_show_page(post)


@bp.route("/obyavlenie/<slug>")
@limiter.limit("120 per minute")
def post_public_legacy(slug):
    from flask import render_template

    from app.routes.post_detail import render_gone_page

    action, post = resolve_public_slug_view(slug)
    if action == "not_found":
        return render_template("errors/404.html"), 404
    if action == "gone":
        return render_gone_page()
    if action in ("show", "redirect"):
        return redirect(post_public_url(post), code=301)
    return render_template("errors/404.html"), 404


@bp.route("/health")
def health():
    from sqlalchemy import text

    from app.extensions import db

    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok"), 200
    except Exception:
        return jsonify(status="error"), 503


@bp.route("/ready")
def ready():
    """Readiness probe for every service required by normal requests."""
    import httpx
    import redis
    from sqlalchemy import text

    from app.extensions import db
    from app.services.storage import _client

    checks = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    try:
        redis.from_url(current_app.config["REDIS_URL"], socket_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    try:
        response = httpx.get(
            f"{current_app.config['TYPESENSE_URL'].rstrip('/')}/health",
            headers={"X-TYPESENSE-API-KEY": current_app.config["TYPESENSE_API_KEY"]},
            timeout=2,
        )
        checks["typesense"] = "ok" if response.json().get("ok") else "error"
    except Exception:
        checks["typesense"] = "error"
    try:
        _client().head_bucket(Bucket=current_app.config["S3_BUCKET"])
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"

    ok = all(value == "ok" for value in checks.values())
    return jsonify(status="ok" if ok else "error", checks=checks), 200 if ok else 503


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
        urls.append({"loc": absolute_url(category_path(category_slug))})
        for city_slug in CITIES:
            urls.append({"loc": absolute_url(city_category_path(city_slug, category_slug))})

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
    category = request.args.get("category", "")
    if (
        category in CATEGORIES
        and not request.args.get("q")
        and not request.args.get("city")
        and not request.args.get("price_min")
        and not request.args.get("price_max")
        and max(request.args.get("page", 1, type=int), 1) == 1
    ):
        return redirect(category_path(category), code=301)
    return _render_listing()


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


@bp.route("/kategoriya/<category_slug>")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def category_page_legacy(category_slug):
    if category_slug not in CATEGORIES:
        return render_template("errors/404.html"), 404
    return _redirect_preserve_query(category_path(category_slug), drop_params={"category"})


@bp.route("/gorod/<city_slug>")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def city_page_legacy(city_slug):
    if city_slug not in CITIES:
        return render_template("errors/404.html"), 404
    return _redirect_preserve_query(city_category_path(city_slug), drop_params={"city"})


@bp.route("/gorod/<city_slug>/<category_slug>")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def city_category_page_legacy(city_slug, category_slug):
    if city_slug not in CITIES or category_slug not in CATEGORIES:
        return render_template("errors/404.html"), 404
    return _redirect_preserve_query(
        city_category_path(city_slug, category_slug),
        drop_params={"city", "category"},
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


@bp.route("/manifest.webmanifest")
def web_manifest():
    response = make_response(render_template("manifest.webmanifest"))
    response.headers["Content-Type"] = "application/manifest+json; charset=utf-8"
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.route("/sw.js")
def service_worker():
    response = make_response(
        render_template("sw.js", static_version=current_app.config.get("STATIC_VERSION", "1"))
    )
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    response.headers["Cache-Control"] = "no-cache"
    return response


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


@bp.route("/<listing_city:city_slug>/<listing_category:category_slug>/")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def city_category_page(city_slug, category_slug):
    return _render_listing(fixed_city=city_slug, fixed_category=category_slug)


@bp.route("/<listing_slug:slug>/")
@limiter.limit(lambda: current_app.config["RATELIMIT_INDEX"])
def category_page(slug):
    if slug in CATEGORIES:
        return _render_listing(fixed_category=slug)
    return _render_listing(fixed_city=slug)
