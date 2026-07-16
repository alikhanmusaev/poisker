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
def post_cover_image(post):
    from listings.utils.post_display import ordered_images

    images = ordered_images(post)
    return images[0] if images else ""


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
