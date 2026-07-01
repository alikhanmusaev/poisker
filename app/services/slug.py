import re

from app.extensions import db
from app.models import Post

_CYRILLIC = {
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
    "й": "y",
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


def slugify(text: str, max_len: int = 55) -> str:
    value = (text or "").strip().lower().replace("ё", "е")
    chars = []
    for ch in value:
        if ch in _CYRILLIC:
            chars.append(_CYRILLIC[ch])
        elif ch.isascii() and ch.isalnum():
            chars.append(ch)
        else:
            chars.append("-")
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-")
    return slug[:max_len].strip("-") or "obyavlenie"


def make_unique_slug(title: str, post_id: str, current_slug: str | None = None) -> str:
    if current_slug:
        existing = Post.query.filter_by(slug=current_slug).first()
        if existing and existing.id == post_id:
            base = current_slug.rsplit("-", 1)[0]
            if base and base == slugify(title):
                return current_slug

    base = slugify(title)
    suffix = post_id.replace("-", "")[:8]
    candidate = f"{base}-{suffix}"
    if not Post.query.filter(Post.slug == candidate, Post.id != post_id).first():
        return candidate

    for i in range(2, 20):
        candidate = f"{base}-{suffix}-{i}"
        if not Post.query.filter(Post.slug == candidate, Post.id != post_id).first():
            return candidate

    return f"{base}-{post_id.replace('-', '')[:12]}"
