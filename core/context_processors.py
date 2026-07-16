from django.conf import settings


def site_context(request):
    from listings.constants import (
        CATEGORIES,
        CATEGORY_LABELS,
        CITIES,
        POPULAR_FEED_CITIES,
        SORT_OPTIONS,
    )

    return {
        "site_name": settings.SITE_NAME,
        "site_tagline": settings.SITE_TAGLINE,
        "site_description": settings.SITE_DESCRIPTION,
        "support_email": settings.SUPPORT_EMAIL,
        "static_version": settings.STATIC_VERSION,
        "categories": CATEGORIES,
        "cities": CITIES,
        "category_labels": CATEGORY_LABELS,
        "sort_options": SORT_OPTIONS,
        "popular_cities": [
            (slug, CITIES[slug]) for slug in POPULAR_FEED_CITIES if slug in CITIES
        ],
    }
