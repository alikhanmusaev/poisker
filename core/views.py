from django.conf import settings
from django.db import connection, models
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from listings.constants import (
    CATEGORIES,
    CATEGORY_LABELS,
    CATEGORY_VISUALS,
    CITIES,
    ALLOWED_SORTS,
    DEFAULT_SEARCH_SORT,
    DEFAULT_SORT,
    RESERVED_SLUGS,
)
from listings.models import Post
from listings.ranking import RankingService
from listings.services.geo_preference import resolve_boost_city
from listings.services.search import suggest as search_suggest
from listings.services.seo_urls import make_seo_slug, post_public_url
from listings.services.smart_query import parse_search_query
from locations.models import Region, Settlement
from locations.services.geo import attach_geo_cookies, clear_geo_cookies, resolve_geo
from locations.services.search import popular_settlements

PER_PAGE = 20


def _render_listing(request, template_name, ctx):
    response = render(request, template_name, ctx)
    return attach_geo_cookies(response, ctx["geo"])


def _strip_all_flag(request):
    qs = request.GET.copy()
    qs.pop("all", None)
    return qs


def _clear_city_and_redirect(request, path):
    qs = _strip_all_flag(request)
    target = path
    if qs:
        target = f"{path}?{qs.urlencode()}"
    return clear_geo_cookies(redirect(target))


def _seo_for_listing(*, geo, category, category_name, search_text):
    site = settings.SITE_NAME
    if geo.scope == "settlement" and geo.settlement is not None:
        place = geo.settlement.name
        if category:
            return (
                f"{category_name} в {place} — объявления на {site}",
                f"{category_name} в {place}: свежие объявления на «{site}». "
                "Купить и продать на доске объявлений России.",
            )
        return (
            f"Объявления в {place} — купить и продать на {site}",
            f"Бесплатные объявления в {place} на «{site}». "
            "Недвижимость, авто, услуги и товары.",
        )
    if geo.scope == "region" and geo.region is not None:
        place = geo.region.name
        if category:
            return (
                f"{category_name} в регионе {place} — объявления на {site}",
                f"{category_name} в регионе {place} на «{site}».",
            )
        return (
            f"Объявления в {place} — {site}",
            f"Бесплатные объявления в регионе {place} на «{site}».",
        )
    if category:
        return (
            f"{category_name} — объявления по России | {site}",
            f"Объявления в категории «{category_name}» по всей России на «{site}».",
        )
    if search_text:
        return f"Поиск: {search_text} | {site}", settings.SITE_DESCRIPTION
    return (
        f"Доска объявлений России — купить и продать на {site}",
        settings.SITE_DESCRIPTION,
    )


def _listing_h1(geo, category_name=""):
    if category_name and geo.scope == "settlement" and geo.settlement:
        return f"{category_name} в {geo.settlement.name}"
    if category_name and geo.scope == "region" and geo.region:
        return f"{category_name} в {geo.region.name}"
    if category_name:
        return f"{category_name} по России"
    if geo.scope == "settlement" and geo.settlement:
        return f"Объявления в {geo.settlement.name}"
    if geo.scope == "region" and geo.region:
        return f"Объявления в {geo.region.name}"
    return "Объявления по всей России"


def _listing_context(request, *, fixed_settlement=None, fixed_region=None, fixed_category=None):
    raw_query = request.GET.get("q", "").strip()
    parsed = parse_search_query(raw_query)
    legacy_city = request.GET.get("city", "") or parsed.get("city") or ""
    legacy_settlement = None
    if fixed_settlement is None and fixed_region is None and legacy_city:
        legacy_settlement = (
            Settlement.objects.filter(slug=legacy_city, is_active=True)
            .select_related("region")
            .order_by(
                models.Case(
                    models.When(region__code="12", then=models.Value(0)),
                    default=models.Value(1),
                ),
                "-population",
            )
            .first()
        )
    geo = resolve_geo(
        request,
        url_settlement=fixed_settlement or legacy_settlement,
        url_region=fixed_region,
    )
    city = geo.settlement.slug if geo.settlement is not None else legacy_city
    category = fixed_category or request.GET.get("category", "") or parsed.get("category") or ""
    search_text = parsed.get("text") or raw_query

    sort = request.GET.get("sort", "")
    if sort not in ALLOWED_SORTS:
        sort = DEFAULT_SEARCH_SORT if search_text else DEFAULT_SORT

    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1
    offset = (page - 1) * PER_PAGE

    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    price_min = int(price_min) if price_min and str(price_min).isdigit() else parsed.get("price_min")
    price_max = int(price_max) if price_max and str(price_max).isdigit() else parsed.get("price_max")

    region_id = None
    if geo.scope == "region" and geo.region is not None:
        region_id = geo.region.id

    settlement_name = geo.settlement.name if geo.settlement is not None else ""
    region_name = ""
    if geo.region is not None:
        region_name = geo.region.name
    elif geo.settlement is not None:
        region_name = geo.settlement.region.name

    has_filters = bool(price_min is not None or price_max is not None)
    ranking_mode = None
    if search_text:
        ranking_mode = "search"
    elif category:
        ranking_mode = "category"
    else:
        ranking_mode = "home"

    ranked = RankingService().build(
        query=search_text,
        category=category or None,
        settlement=geo.settlement,
        region=geo.region if geo.settlement is None else None,
        boost_city=resolve_boost_city(
            request, filtered_city=city if geo.settlement is not None else None
        ),
        price_min=price_min,
        price_max=price_max,
        has_filters=has_filters,
        expanded_terms=parsed.get("expanded_terms"),
        limit=PER_PAGE,
        offset=offset,
        page=page,
        mode=ranking_mode,
    )
    results = ranked.results
    total = ranked.total
    has_next = page * PER_PAGE < total

    category_name = CATEGORY_LABELS.get(category, "") if category else ""
    if geo.settlement is not None:
        city_name = geo.settlement.name
    elif geo.region is not None:
        city_name = geo.region.name
    else:
        city_name = CITIES.get(city, city) if city else "Россия"

    seo_title, seo_description = _seo_for_listing(
        geo=geo, category=category, category_name=category_name, search_text=search_text
    )
    listing_h1 = _listing_h1(geo, category_name)

    canonical_url = f"https://{settings.APP_DOMAIN}{request.path}"

    breadcrumbs = [{"name": "Главная", "url": "/"}]
    if geo.region is not None:
        breadcrumbs.append(
            {"name": geo.region.name, "url": f"/{geo.region.slug}/"}
        )
    if geo.settlement is not None:
        breadcrumbs.append(
            {
                "name": geo.settlement.name,
                "url": f"/{geo.settlement.region.slug}/{geo.settlement.slug}/",
            }
        )
    if category:
        breadcrumbs.append(
            {
                "name": category_name,
                "url": request.path,
            }
        )

    ctx = {
        "query": raw_query,
        "search_text": search_text,
        "city": city,
        "category": category,
        "category_name": category_name,
        "category_visual": CATEGORY_VISUALS.get(category),
        "city_name": city_name,
        "listing_h1": listing_h1,
        "sort": sort,
        "page": page,
        "results": results,
        "promoted_results": ranked.promoted,
        "feed_sections": ranked.sections,
        "ranking_mode": ranked.mode,
        "total": total,
        "local_total": ranked.local_total,
        "geo_fallback": ranked.geo_fallback,
        "geo_fallback_label": ranked.geo_fallback_label,
        "has_next": has_next,
        "price_min": price_min,
        "price_max": price_max,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "canonical_url": canonical_url,
        "listing_path": request.path,
        "fixed_city": city if fixed_settlement else None,
        "fixed_category": fixed_category,
        "geo": geo,
        "breadcrumbs": breadcrumbs,
        "popular_settlements": popular_settlements(12),
        "robots_noindex": bool(
            search_text
            or page > 1
            or sort not in (DEFAULT_SORT, DEFAULT_SEARCH_SORT)
            or ranked.geo_fallback
            or (fixed_settlement is not None and ranked.local_total == 0)
            or (fixed_region is not None and ranked.local_total == 0)
        ),
        "bookmarked_post_ids": set(),
    }
    if request.user.is_authenticated:
        from bookmarks.services import bookmarked_post_ids_for

        post_ids = []
        for bucket in (results, ranked.promoted, *(ranked.sections.values() if ranked.sections else [])):
            for item in bucket:
                post = item.get("post") if isinstance(item, dict) else item
                if post is not None and getattr(post, "pk", None):
                    post_ids.append(post.pk)
        ctx["bookmarked_post_ids"] = bookmarked_post_ids_for(request.user, post_ids)
    return ctx


def index(request):
    if request.GET.get("all") == "1":
        return _clear_city_and_redirect(request, "/")
    ctx = _listing_context(request)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def category_listing(request, category_slug):
    if category_slug not in CATEGORIES:
        raise Http404
    if request.GET.get("all") == "1":
        return _clear_city_and_redirect(request, f"/{category_slug}/")
    ctx = _listing_context(request, fixed_category=category_slug)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def city_listing(request, city_slug):
    settlement = (
        Settlement.objects.filter(slug=city_slug, is_active=True)
        .select_related("region")
        .order_by(
            models.Case(
                models.When(region__code="12", then=models.Value(0)),
                default=models.Value(1),
            ),
            "-population",
        )
        .first()
    )
    if settlement is None:
        raise Http404
    ctx = _listing_context(request, fixed_settlement=settlement)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def region_listing(request, region_slug):
    region = get_object_or_404(Region, slug=region_slug, is_active=True)
    ctx = _listing_context(request, fixed_region=region)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def region_settlement_listing(request, region_slug, settlement_slug):
    settlement = get_object_or_404(
        Settlement.objects.select_related("region"),
        slug=settlement_slug,
        region__slug=region_slug,
        is_active=True,
        region__is_active=True,
    )
    ctx = _listing_context(request, fixed_settlement=settlement)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def city_category_listing(request, city_slug, category_slug):
    # Legacy: /grozny/avto/  OR new: /chechenskaya-respublika/grozny/ when second is not category
    if category_slug in CATEGORIES:
        settlement = (
            Settlement.objects.filter(slug=city_slug, is_active=True)
            .select_related("region")
            .order_by(
                models.Case(
                    models.When(region__code="12", then=models.Value(0)),
                    default=models.Value(1),
                ),
                "-population",
            )
            .first()
        )
        if settlement is None:
            # /<region>/<category>/
            region = Region.objects.filter(slug=city_slug, is_active=True).first()
            if region is None:
                raise Http404
            ctx = _listing_context(
                request, fixed_region=region, fixed_category=category_slug
            )
        else:
            ctx = _listing_context(
                request, fixed_settlement=settlement, fixed_category=category_slug
            )
    else:
        return region_settlement_listing(request, city_slug, category_slug)
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def region_settlement_category_listing(request, region_slug, settlement_slug, category_slug):
    if category_slug not in CATEGORIES:
        raise Http404
    settlement = get_object_or_404(
        Settlement.objects.select_related("region"),
        slug=settlement_slug,
        region__slug=region_slug,
        is_active=True,
        region__is_active=True,
    )
    ctx = _listing_context(
        request, fixed_settlement=settlement, fixed_category=category_slug
    )
    if request.headers.get("HX-Request"):
        return _render_listing(request, "partials/feed_panel.html", ctx)
    return _render_listing(request, "index.html", ctx)


def post_public(request, city_slug, category_slug, slug, post_id):
    post = get_object_or_404(
        Post.objects.select_related("user", "settlement__region"), pk=post_id
    )
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
    from core.http import get_client_ip
    from core.ratelimit import hit_rate_limit

    ip = get_client_ip(request) or "unknown"
    if hit_rate_limit(
        f"suggest:{ip}",
        limit=getattr(settings, "SUGGEST_RATE_LIMIT_PER_MINUTE", 60),
        window_seconds=60,
        fail_closed=True,
    ):
        return HttpResponse(status=429)
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


GOOGLE_SITE_VERIFICATION_FILE = "google05c2cca6c3f18f09.html"


def google_site_verification(request):
    return HttpResponse(
        f"google-site-verification: {GOOGLE_SITE_VERIFICATION_FILE}",
        content_type="text/html; charset=utf-8",
    )


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


def sitemap_xml(request):
    now = timezone.now()
    active = Post.objects.filter(status="published", expires_at__gte=now)
    posts = list(
        active.select_related("settlement__region").order_by("-updated_at")[:5000]
    )
    base = f"https://{settings.APP_DOMAIN}"
    entries = [(f"{base}/", None)]
    for slug in CATEGORIES:
        entries.append((f"{base}/{slug}/", None))

    region_slugs = (
        active.exclude(settlement__isnull=True)
        .values_list("settlement__region__slug", flat=True)
        .distinct()
    )
    for region_slug in region_slugs:
        if region_slug:
            entries.append((f"{base}/{region_slug}/", None))

    settlement_rows = (
        active.exclude(settlement__isnull=True)
        .values_list("settlement__region__slug", "settlement__slug")
        .distinct()[:5000]
    )
    for region_slug, settlement_slug in settlement_rows:
        if region_slug and settlement_slug:
            entries.append((f"{base}/{region_slug}/{settlement_slug}/", None))

    # Legacy city URLs that still have ads without settlement FK
    legacy_cities = (
        active.filter(settlement__isnull=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
    )
    for city_slug in legacy_cities:
        entries.append((f"{base}/{city_slug}/", None))

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
    region = Region.objects.filter(slug=slug, is_active=True).first()
    if region is not None:
        return region_listing(request, slug)
    settlement = (
        Settlement.objects.filter(slug=slug, is_active=True)
        .select_related("region")
        .order_by(
            models.Case(
                models.When(region__code="12", then=models.Value(0)),
                default=models.Value(1),
            ),
            "-population",
        )
        .first()
    )
    if settlement is not None:
        return city_listing(request, slug)
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
        {"reason": reason, "robots_noindex": True},
        status=403,
    )


def _error_page(request, template_name, status):
    return render(request, template_name, {"robots_noindex": True}, status=status)


def bad_request(request, exception):
    return _error_page(request, "errors/400.html", 400)


def permission_denied(request, exception):
    return _error_page(request, "errors/403.html", 403)


def page_not_found(request, exception):
    return _error_page(request, "errors/404.html", 404)


def server_error(request):
    """Render 500 without request context processors — they may be the failure."""
    from django.template.loader import get_template

    try:
        html = get_template("errors/500.html").render(
            {
                "site_name": getattr(settings, "SITE_NAME", "Поискер"),
                "static_version": getattr(settings, "STATIC_VERSION", ""),
            }
        )
        return HttpResponse(html, status=500)
    except Exception:
        return HttpResponse(
            "<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Ошибка сервера</title></head><body>"
            "<h1>На сервере произошла ошибка</h1>"
            "<p>Попробуйте обновить страницу или вернуться позже.</p>"
            "<p><a href='/'>На главную</a></p></body></html>",
            status=500,
            content_type="text/html; charset=utf-8",
        )


def _no_cache_headers(response):
    # Service worker and manifest must be checked again on every app launch.
    # Static assets themselves are immutable and use a content version.
    response["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
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
        {
            "static_version": getattr(settings, "STATIC_VERSION", "1"),
            "firebase_web_config": getattr(settings, "FIREBASE_WEB_CONFIG", {}) or {},
        },
    )
    response["Content-Type"] = "application/javascript; charset=utf-8"
    response["Service-Worker-Allowed"] = "/"
    return _no_cache_headers(response)
