import re
import unicodedata

from django.urls import reverse

from listings.models import Post

_CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _transliterate(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    chars = []
    for ch in text:
        if ch in _CYRILLIC_TO_LATIN:
            chars.append(_CYRILLIC_TO_LATIN[ch])
        elif "a" <= ch <= "z" or "0" <= ch <= "9":
            chars.append(ch)
        elif ch.isspace() or ch in "-_./":
            chars.append("-")
        else:
            chars.append("-")
    return "".join(chars)


def make_seo_slug(title: str, city: str) -> str:
    base = re.sub(r"-+", "-", _transliterate(title)).strip("-")[:80] or "obyavlenie"
    city_part = re.sub(r"-+", "-", _transliterate(city or "")).strip("-")[:24] or "city"
    return f"{base}-{city_part}"[:120]


def post_public_kwargs(post: Post) -> dict:
    return {
        "city_slug": post.city,
        "category_slug": post.category,
        "slug": post.slug or make_seo_slug(post.title, post.city),
        "post_id": post.pk,
    }


def post_public_url(post: Post) -> str:
    if post.city and post.category and post.pk:
        return reverse("core:post_public", kwargs=post_public_kwargs(post))
    return reverse("listings:show", kwargs={"post_id": post.pk})
