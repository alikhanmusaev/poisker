from django import template
from django.urls import reverse
from django.utils import timezone

from listings.services.seo_urls import post_public_url as build_post_public_url

register = template.Library()


def _plural_ru(count, forms):
    try:
        n = abs(int(count))
    except (TypeError, ValueError):
        return forms.split(",")[2]
    parts = forms.split(",")
    if len(parts) != 3:
        return parts[-1]
    if n % 10 == 1 and n % 100 != 11:
        return parts[0]
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return parts[1]
    return parts[2]


@register.simple_tag
def category_path(slug):
    return f"/{slug}/"


@register.simple_tag
def city_category_path(city, category=None):
    if category:
        return f"/{city}/{category}/"
    return f"/{city}/"


@register.simple_tag
def settlement_path(settlement, category=None):
    if settlement is None:
        return "/"
    base = f"/{settlement.region.slug}/{settlement.slug}/"
    if category:
        return f"{base}{category}/"
    return base


@register.simple_tag
def region_path(region, category=None):
    if region is None:
        return "/"
    if category:
        return f"/{region.slug}/{category}/"
    return f"/{region.slug}/"


@register.simple_tag
def geo_listing_path(geo, category=None):
    """Build listing URL for current GeoSelection."""
    if geo is None:
        return f"/{category}/" if category else "/"
    if getattr(geo, "scope", None) == "settlement" and geo.settlement is not None:
        return settlement_path(geo.settlement, category)
    if getattr(geo, "scope", None) == "region" and geo.region is not None:
        return region_path(geo.region, category)
    return f"/{category}/" if category else "/"


@register.filter
def post_location(post):
    return getattr(post, "location_label", "") or ""


@register.simple_tag
def post_cover_image(post):
    from listings.utils.post_display import ordered_images

    images = ordered_images(post)
    return images[0] if images else ""


@register.filter
def image_sm(url):
    """Thumb JPEG URL for compact UI (avatars-sized previews)."""
    from listings.services.storage import image_variant_url

    return image_variant_url(url, size="sm", fmt="jpeg")


@register.inclusion_tag("partials/responsive_img.html")
def responsive_img(
    url,
    alt="",
    img_class="",
    sizes="(max-width: 640px) 50vw, 320px",
    width=None,
    height=None,
    loading="lazy",
    deferred=False,
    prefer="sm",
    fetchpriority=None,
    card=False,
):
    """WebP + JPEG srcset. prefer=sm for cards, prefer=full for detail gallery.

    card=True limits srcset to thumb only (better LCP on feed).
    """
    from listings.services.storage import image_variant_url

    jpeg_full = image_variant_url(url, size="full", fmt="jpeg")
    jpeg_sm = image_variant_url(url, size="sm", fmt="jpeg")
    webp_full = image_variant_url(url, size="full", fmt="webp")
    webp_sm = image_variant_url(url, size="sm", fmt="webp")
    if card:
        jpeg_srcset = f"{jpeg_sm} 360w"
        webp_srcset = f"{webp_sm} 360w"
        jpeg_src = jpeg_sm
    else:
        jpeg_srcset = f"{jpeg_sm} 360w, {jpeg_full} 960w"
        webp_srcset = f"{webp_sm} 360w, {webp_full} 960w"
        jpeg_src = jpeg_sm if prefer == "sm" else jpeg_full
    return {
        "alt": alt,
        "img_class": img_class,
        "sizes": sizes,
        "width": width,
        "height": height,
        "loading": loading,
        "deferred": bool(deferred),
        "fetchpriority": fetchpriority or "",
        "jpeg_full": jpeg_full,
        "jpeg_sm": jpeg_sm,
        "jpeg_src": jpeg_src,
        "jpeg_srcset": jpeg_srcset,
        "webp_srcset": webp_srcset,
    }


@register.simple_tag
def post_public_url(post):
    return build_post_public_url(post)


@register.simple_tag
def post_image_alt(title, index, total):
    try:
        total = int(total)
        index = int(index)
    except (TypeError, ValueError):
        return title
    if total > 1:
        return f"{title} — фото {index} из {total}"
    return title


@register.filter
def get_item(mapping, key):
    if not mapping:
        return key
    return mapping.get(key, key)


@register.filter
def format_price(value):
    if value is None:
        return ""
    return f"{int(value):,}".replace(",", " ")


@register.filter
def post_price_display(price):
    if price is None:
        return "По договорённости"
    return f"{format_price(price)} ₽"


@register.filter
def relative_time(value):
    if not value:
        return ""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    delta = timezone.now() - value
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 3600:
        minutes = max(seconds // 60, 1)
        return f"{minutes} {_plural_ru(minutes, 'минуту,минуты,минут')} назад"
    if seconds < 86400:
        hours = max(seconds // 3600, 1)
        return f"{hours} {_plural_ru(hours, 'час,часа,часов')} назад"
    days = seconds // 86400
    if days == 1:
        return "вчера"
    if days < 7:
        return f"{days} {_plural_ru(days, 'день,дня,дней')} назад"
    return value.strftime("%d.%m.%Y")


@register.filter
def plural_ru(count, forms):
    return _plural_ru(count, forms)


@register.filter
def days_until_expiry(post):
    from accounts.services.seller_stats import days_until_expiry as _days

    return _days(post)
