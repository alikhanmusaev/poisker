from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from listings.constants import (
    CATEGORIES,
    CATEGORY_LABELS,
    CITIES,
    ALLOWED_SORTS,
    DEFAULT_SEARCH_SORT,
    DEFAULT_SORT,
    RESERVED_SLUGS,
)
from listings.models import Post
from listings.services.geo_preference import (
    attach_city_cookie,
    clear_city_cookie,
    preferred_city_from_request,
    resolve_boost_city,
)
from listings.services.search import search_posts, suggest as search_suggest
from listings.services.seo_urls import make_seo_slug, post_public_url
from listings.services.smart_query import parse_search_query

PER_PAGE = 20


def _render_listing(request, template_name, ctx):
    response = render(request, template_name, ctx)
    city = ctx.get("city") or None
    if city:
        return attach_city_cookie(response, city)
    return response


def _strip_all_flag(request):
    qs = request.GET.copy()
    qs.pop("all", None)
    return qs


def _preferred_city_redirect(request, *, category=None):
    """Keep the last chosen city when opening home / category without a city."""
    if request.GET.get("all") == "1":
        return None
    preferred = preferred_city_from_request(request)
    if not preferred:
        return None
    path = f"/{preferred}/{category}/" if category else f"/{preferred}/"
    qs = _strip_all_flag(request)
    if qs:
        path = f"{path}?{qs.urlencode()}"
    return redirect(path)


def _clear_city_and_redirect(request, path):
    qs = _strip_all_flag(request)
    target = path
    if qs:
        target = f"{path}?{qs.urlencode()}"
    return clear_city_cookie(redirect(target))


def _listing_context(request, *, fixed_city=None, fixed_category=None):
    raw_query = request.GET.get("q", "").strip()
    parsed = parse_search_query(raw_query)
    city = fixed_city or request.GET.get("city", "") or parsed.get("city") or ""
    category = fixed_category or request.GET.get("category", "") or parsed.get("category") or ""
    search_text = parsed.get("text") or raw_query

    sort = request.GET.get("sort", "")
    if sort not in ALLOWED_SORTS:
        sort = DEFAULT_SEARCH_SORT if search_text else DEFAULT_SORT

    page = max(int(request.GET.get("page", 1)), 1)
    offset = (page - 1) * PER_PAGE

    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    price_min = int(price_min) if price_min and str(price_min).isdigit() else parsed.get("price_min")
    price_max = int(price_max) if price_max and str(price_max).isdigit() else parsed.get("price_max")

    results, total = search_posts(
        query=search_text,
        city=city or None,
        category=category or None,
        price_min=price_min,
        price_max=price_max,
        sort=sort,
        limit=PER_PAGE,
        offset=offset,
        expanded_terms=parsed.get("expanded_terms"),
        boost_city=resolve_boost_city(request, filtered_city=city or None),
    )
    has_next = page * PER_PAGE < total

    category_name = CATEGORY_LABELS.get(category, "") if category else ""
    city_name = CITIES.get(city, city) if city else ""

    if category and city:
        seo_title = f"{category_name} — {city_name} | {settings.SITE_NAME}"
        seo_description = (
            f"{category_name} в городе {city_name}: свежие объявления на «{settings.SITE_NAME}». "
            f"Бесплатная доска объявлений по Чеченской Республике."
        )
    elif category:
        seo_title = f"{category_name} | {settings.SITE_NAME}"
        seo_description = (
            f"Объявления в категории «{category_name}» на «{settings.SITE_NAME}». "
            f"Поиск по Чеченской Республике."
        )
    elif city:
        seo_title = f"Объявления {city_name} | {settings.SITE_NAME}"
        seo_description = (
            f"Бесплатные объявления в городе {city_name} на «{settings.SITE_NAME}». "
            f"Недвижимость, авто, услуги и товары."
        )
    elif search_text:
        seo_title = f"Поиск: {search_text} | {settings.SITE_NAME}"
        seo_description = settings.SITE_DESCRIPTION
    else:
        seo_title = f"{settings.SITE_NAME} — {settings.SITE_TAGLINE}"
        seo_description = settings.SITE_DESCRIPTION

    canonical_url = f"https://{settings.APP_DOMAIN}{request.path}"

    ctx = {
        "query": raw_query,
        "search_text": search_text,
        "city": city,
        "category": category,
        "category_name": category_name,
        "city_name": city_name,
        "sort": sort,
        "page": page,
        "results": results,
        "total": total,
        "has_next": has_next,
        "price_min": price_min,
        "price_max": price_max,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "listing_path": request.path,
        "fixed_city": fixed_city,
        "fixed_category": fixed_category,
        "robots_noindex": bool(search_text or page > 1 or sort not in (DEFAULT_SORT, DEFAULT_SEARCH_SORT)),
        "category_bookmarked": False,
        "bookmarked_post_ids": set(),
    }
    if request.user.is_authenticated:
        from bookmarks.services import bookmarked_post_ids_for, is_category_bookmarked

        if category:
            ctx["category_bookmarked"] = is_category_bookmarked(request.user, category)
        post_ids = []
        for item in results:
            post = item.get("post") if isinstance(item, dict) else item
            if post is not None and getattr(post, "pk", None):
                post_ids.append(post.pk)
        ctx["bookmarked_post_ids"] = bookmarked_post_ids_for(request.user, post_ids)
    return ctx


def index(request):
    if request.GET.get("all") == "1":
        return _clear_city_and_redirect(request, "/")
    preferred_redirect = _preferred_city_redirect(request)
    if preferred_redirect:
        return preferred_redirect
    ctx = _listing_context(request)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def category_listing(request, category_slug):
    if category_slug not in CATEGORIES:
        raise Http404
    if request.GET.get("all") == "1":
        return _clear_city_and_redirect(request, f"/{category_slug}/")
    preferred_redirect = _preferred_city_redirect(request, category=category_slug)
    if preferred_redirect:
        return preferred_redirect
    ctx = _listing_context(request, fixed_category=category_slug)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def city_listing(request, city_slug):
    if city_slug not in CITIES:
        raise Http404
    ctx = _listing_context(request, fixed_city=city_slug)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def city_category_listing(request, city_slug, category_slug):
    if city_slug not in CITIES or category_slug not in CATEGORIES:
        raise Http404
    ctx = _listing_context(request, fixed_city=city_slug, fixed_category=category_slug)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def post_public(request, city_slug, category_slug, slug, post_id):
    post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)
    if post.city != city_slug or post.category != category_slug:
        raise Http404
    if post.status != "published" or post.expires_at <= timezone.now():
        if not (request.user.is_authenticated and post.user_id == request.user.id):
            raise Http404
    canonical_slug = post.slug or make_seo_slug(post.title, post.city)
    if slug != canonical_slug:
        return redirect(post_public_url(post), permanent=True)
    from listings.services.show_context import build_show_context, increment_views

    increment_views(request, post)
    return render(request, "listings/show.html", build_show_context(request, post))


def post_public_legacy(request, city_slug, category_slug, slug):
    posts = Post.objects.filter(slug=slug, city=city_slug, category=category_slug, status="published")
    post = posts.first()
    if not post or post.expires_at <= timezone.now():
        raise Http404
    return redirect(post_public_url(post), permanent=True)


def suggest_view(request):
    if not request.headers.get("HX-Request"):
        raise Http404
    query = request.GET.get("q", "").strip()
    items = search_suggest(query) if query else []
    return render(request, "partials/suggest.html", {"items": items, "query": query})


def health(request):
    return JsonResponse({"status": "ok"})


def ready(request):
    checks = {}
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    try:
        import httpx

        response = httpx.get(
            f"{settings.TYPESENSE_URL.rstrip('/')}/health",
            headers={"X-TYPESENSE-API-KEY": settings.TYPESENSE_API_KEY},
            timeout=2,
        )
        checks["typesense"] = "ok" if response.json().get("ok") else "error"
    except Exception:
        checks["typesense"] = "error"
    ok = all(v == "ok" for v in checks.values())
    return JsonResponse({"status": "ok" if ok else "error", "checks": checks}, status=200 if ok else 503)


def privacy(request):
    return render(request, "privacy.html")


def terms(request):
    return render(request, "terms.html")


def pdn_consent(request):
    return render(request, "pdn_consent.html")


def guidelines(request):
    return render(request, "guidelines.html")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /accounts/",
        "Disallow: /moderation/",
        "Disallow: /admin/",
        "Disallow: /messages/",
        "Disallow: /bookmarks/",
        "Disallow: /posts/",
        f"Sitemap: https://{settings.APP_DOMAIN}/sitemap.xml",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def assetlinks_json(request):
    """Digital Asset Links for Android App Links (ru.poisker.app)."""
    import json

    # Debug keystore SHA-256 (androiddebugkey). Replace/add Play App Signing cert before production verify.
    fingerprints = [
        "2A:0E:76:5E:94:69:3E:9E:13:BC:52:F0:57:FA:0D:92:1D:8B:6B:DD:04:0A:47:4F:1D:D8:9F:9A:54:7C:B7:FB",
    ]
    release_fp = (getattr(settings, "ANDROID_RELEASE_SHA256", "") or "").strip()
    if release_fp and release_fp not in fingerprints:
        fingerprints.append(release_fp)

    payload = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "ru.poisker.app",
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
    return HttpResponse(
        json.dumps(payload, ensure_ascii=False, indent=2),
        content_type="application/json",
    )


def sitemap_xml(request):
    posts = list(
        Post.objects.filter(status="published", expires_at__gte=timezone.now())
        .order_by("-updated_at")[:5000]
    )
    base = f"https://{settings.APP_DOMAIN}"
    entries = [(f"{base}/", None)]
    for slug in CATEGORIES:
        entries.append((f"{base}/{slug}/", None))
    for slug in CITIES:
        entries.append((f"{base}/{slug}/", None))
    for city_slug in CITIES:
        for category_slug in CATEGORIES:
            entries.append((f"{base}/{city_slug}/{category_slug}/", None))
    for path in ("/privacy", "/terms", "/consent", "/guidelines"):
        entries.append((f"{base}{path}", None))
    for post in posts:
        lastmod = post.updated_at.date().isoformat() if post.updated_at else None
        entries.append((f"{base}{post_public_url(post)}", lastmod))
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in entries:
        body.append("  <url>")
        body.append(f"    <loc>{loc}</loc>")
        if lastmod:
            body.append(f"    <lastmod>{lastmod}</lastmod>")
        body.append("  </url>")
    body.append("</urlset>")
    return HttpResponse("\n".join(body), content_type="application/xml")


def slug_router(request, slug):
    if slug in RESERVED_SLUGS:
        raise Http404
    if slug in CATEGORIES:
        return category_listing(request, slug)
    if slug in CITIES:
        return city_listing(request, slug)
    raise Http404


def csrf_failure(request, reason=""):
    """Duplicate POST after login() rotates CSRF — send user to profile instead of 403."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    return render(
        request,
        "errors/csrf.html",
        {"reason": reason},
        status=403,
    )


def _no_cache_headers(response):
    response["Cache-Control"] = "no-cache"
    return response


def offline(request):
    return render(request, "offline.html", {"robots_noindex": True})


def web_manifest(request):
    response = render(request, "manifest.webmanifest")
    response["Content-Type"] = "application/manifest+json; charset=utf-8"
    return _no_cache_headers(response)


def service_worker(request):
    response = render(
        request,
        "sw.js",
        {"static_version": getattr(settings, "STATIC_VERSION", "1")},
    )
    response["Content-Type"] = "application/javascript; charset=utf-8"
    return _no_cache_headers(response)
