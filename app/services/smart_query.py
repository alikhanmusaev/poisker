import re

from app.constants import (
    BRAND_ALIASES,
    CATEGORIES,
    CATEGORY_KEYWORDS,
    CATEGORY_LABELS,
    CITIES,
)


PRICE_RE = r"(\d[\d\s]{0,12}\s*(?:к|k|тыс\.?|тысяч)?)"


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower().replace("ё", "е")).strip()


def _price_to_int(value: str) -> int | None:
    raw = (value or "").strip().lower().replace(" ", "")
    multiplier = 1000 if re.search(r"(?:к|k|тыс)", raw) else 1
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    return int(digits) * multiplier


CITY_ALIASES = {
    slug: slug for slug in CITIES
}
for slug, label in CITIES.items():
    normalized_label = _norm(label)
    CITY_ALIASES[normalized_label] = slug
    CITY_ALIASES[normalized_label.replace("-", " ")] = slug
    CITY_ALIASES[slug.replace("-", " ")] = slug

CATEGORY_ALIASES = {
    slug: slug for slug in CATEGORIES
}
for slug, label in CATEGORY_LABELS.items():
    normalized_label = _norm(label)
    CATEGORY_ALIASES[normalized_label] = slug
    CATEGORY_ALIASES[slug.replace("-", " ")] = slug


def _expand_terms(text: str) -> list[str]:
    terms = []
    seen = set()
    for token in re.findall(r"[\wа-яё]+", _norm(text), flags=re.IGNORECASE):
        if len(token) < 2:
            continue
        for word in [token, *BRAND_ALIASES.get(token, [])]:
            key = word.lower()
            if key not in seen:
                seen.add(key)
                terms.append(word)
    return terms or ([text] if text else [])


def _infer_category(cleaned: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    for keyword, slug in sorted(CATEGORY_KEYWORDS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
        if re.search(pattern, cleaned):
            return slug
    return None


def parse_search_query(raw_query: str) -> dict:
    raw = raw_query or ""
    normalized = _norm(raw)
    cleaned = f" {normalized} "

    city = None
    for alias, slug in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(pattern, cleaned):
            city = slug
            cleaned = re.sub(pattern, " ", cleaned)
            break

    category = None
    for alias, slug in sorted(CATEGORY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(pattern, cleaned):
            category = slug
            cleaned = re.sub(pattern, " ", cleaned)
            break

    price_min = None
    price_max = None

    between_match = re.search(
        rf"(?:от)\s*{PRICE_RE}\s*(?:до)\s*{PRICE_RE}",
        cleaned,
    )
    if between_match:
        full = between_match.group(0)
        has_thousands = bool(re.search(r"(?:к|k|тыс)", full))
        price_min = _price_to_int(between_match.group(1))
        price_max = _price_to_int(between_match.group(2))
        if has_thousands:
            if price_min is not None and price_min < 1000:
                price_min *= 1000
            if (
                price_max is not None
                and price_max < 1000
                and not re.search(r"(?:к|k|тыс)", between_match.group(2))
            ):
                price_max *= 1000
        cleaned = cleaned.replace(between_match.group(0), " ")

    range_match = re.search(rf"{PRICE_RE}\s*(?:-|–|—)\s*{PRICE_RE}", cleaned)
    if range_match:
        price_min = _price_to_int(range_match.group(1))
        price_max = _price_to_int(range_match.group(2))
        cleaned = cleaned.replace(range_match.group(0), " ")

    max_match = re.search(rf"(?:до|не дороже|дешевле|<=)\s*{PRICE_RE}", cleaned)
    if max_match:
        price_max = _price_to_int(max_match.group(1))
        cleaned = cleaned.replace(max_match.group(0), " ")

    min_match = re.search(rf"(?:от|дороже|>=)\s*{PRICE_RE}", cleaned)
    if min_match:
        price_min = _price_to_int(min_match.group(1))
        cleaned = cleaned.replace(min_match.group(0), " ")

    with_photo = bool(re.search(r"(?:с фото|фото|фотографи)", cleaned))
    if with_photo:
        cleaned = re.sub(r"(?:с фото|фото|фотографи\w*)", " ", cleaned)

    with_price = bool(re.search(r"с\s+ценой", cleaned))
    if with_price:
        cleaned = re.sub(r"с\s+ценой", " ", cleaned)

    search_text = re.sub(r"\b(?:руб|рублей|р|₽|цена)\b", " ", cleaned)
    search_text = re.sub(r"\s+", " ", search_text).strip()

    category = _infer_category(f" {search_text} ", category)
    expanded_terms = _expand_terms(search_text)

    return {
        "text": search_text,
        "city": city,
        "category": category,
        "price_min": price_min,
        "price_max": price_max,
        "with_photo": with_photo,
        "with_price": with_price,
        "expanded_terms": expanded_terms,
    }


def smart_suggestions(raw_query: str, limit: int = 5) -> list[str]:
    query = _norm(raw_query)
    if len(query) < 2:
        return []

    items = []
    for label in CITIES.values():
        if _norm(label).startswith(query):
            items.append(label)
    for label in CATEGORY_LABELS.values():
        if _norm(label).startswith(query):
            items.append(label)

    return items[:limit]
