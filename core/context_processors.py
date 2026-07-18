from django.conf import settings


def site_context(request):
    from listings.constants import (
        CATEGORIES,
        CATEGORY_LABELS,
        CITIES,
        CONDITION_LABELS,
        SORT_OPTIONS,
    )
    from locations.services.geo import resolve_geo
    from locations.services.search import popular_settlements

    geo = getattr(request, "geo", None)
    if geo is None:
        try:
            geo = resolve_geo(request)
        except Exception:
            geo = None

    popular = []
    try:
        popular = popular_settlements(12)
    except Exception:
        popular = []

    return {
        "site_name": settings.SITE_NAME,
        "site_tagline": settings.SITE_TAGLINE,
        "site_description": settings.SITE_DESCRIPTION,
        "support_email": settings.SUPPORT_EMAIL,
        "static_version": settings.STATIC_VERSION,
        "pdn_consent_version": getattr(settings, "PDN_CONSENT_VERSION", ""),
        "operator_name": getattr(settings, "OPERATOR_NAME", ""),
        "operator_address": getattr(settings, "OPERATOR_ADDRESS", ""),
        "operator_inn": getattr(settings, "OPERATOR_INN", ""),
        "operator_ogrnip": getattr(settings, "OPERATOR_OGRNIP", ""),
        "categories": CATEGORIES,
        "cities": CITIES,
        "category_labels": CATEGORY_LABELS,
        "condition_labels": CONDITION_LABELS,
        "sort_options": SORT_OPTIONS,
        "geo": geo,
        "popular_settlements": popular,
        "popular_cities": [(s.slug, s.name) for s in popular],
    }
