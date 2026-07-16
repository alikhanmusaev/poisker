from listings.data.chechnya_settlements import CHECHNYA_SETTLEMENTS

CITIES = CHECHNYA_SETTLEMENTS

# slug -> (label, lucide icon)
CATEGORIES = {
    "nedvizhimost": ("Недвижимость", "home"),
    "avto": ("Авто", "car"),
    "zapchasti": ("Запчасти", "cog"),
    "elektronika": ("Электроника", "smartphone"),
    "prodazha": ("Личные вещи", "shopping-bag"),
    "dlya-doma": ("Для дома", "sofa"),
    "uslugi": ("Услуги", "wrench"),
    "rabota": ("Работа", "briefcase"),
    "detskie": ("Для детей", "baby"),
    "zhivotnye": ("Животные", "paw-print"),
    "sport": ("Спорт", "dumbbell"),
    "stroitelstvo": ("Строительство", "hammer"),
    "rasteniya": ("Растения", "flower-2"),
    "produkti": ("Продукты", "apple"),
    "biznes": ("Бизнес", "store"),
    "drugoe": ("Другое", "layout-grid"),
}

# Flat labels for forms/selects
CATEGORY_LABELS = {slug: label for slug, (label, _) in CATEGORIES.items()}

# Paths that must not be handled by /<slug>/ listing routes
RESERVED_SLUGS = frozenset({
    "accounts",
    "messages",
    "bookmarks",
    "notifications",
    "admin",
    "moderation",
    "posts",
    "privacy",
    "terms",
    "guidelines",
    "reports",
    "promotions",
    "sitemap.xml",
    "robots.txt",
    "manifest.webmanifest",
    "sw.js",
    "static",
    "media",
    "offline",
    "health",
    ".well-known",
    "obyavlenie",
    "kategoriya",
    "gorod",
    "search",
    "suggest",
})
CATEGORY_ICONS = {slug: icon for slug, (_, icon) in CATEGORIES.items()}

SORT_OPTIONS = {
    "date_desc": "Сначала новые",
    "price_asc": "Сначала дешевле",
    "price_desc": "Сначала дороже",
}

# Internal defaults (not shown in the UI): feed vs search hybrid ranking.
DEFAULT_SORT = "rank"
DEFAULT_SEARCH_SORT = "relevance"
ALLOWED_SORTS = frozenset({*SORT_OPTIONS, DEFAULT_SORT, DEFAULT_SEARCH_SORT})

# Quick picks on the home feed (must exist in CITIES).
POPULAR_FEED_CITIES = (
    "grozny",
    "argun",
    "gudermes",
    "urus-martan",
    "shali",
    "achkhoy-martan",
    "kurchaloy",
    "sernovodskoe",
)

SEARCH_SYNONYMS = {
    "машина": ["авто", "автомобиль"],
    "авто": ["машина", "автомобиль"],
    "кв": ["квартира", "жилье"],
    "квартира": ["кв", "жилье"],
    "тел": ["телефон", "смартфон"],
    "телефон": ["тел", "смартфон"],
}

BRAND_ALIASES = {
    "айфон": ["iphone"],
    "iphone": ["айфон"],
    "самсунг": ["samsung", "samsung galaxy"],
    "samsung": ["самсунг"],
    "ксиоми": ["xiaomi", "redmi"],
    "xiaomi": ["ксиоми", "redmi"],
    "редми": ["redmi", "xiaomi"],
    "redmi": ["редми", "xiaomi"],
    "шевроле": ["chevrolet"],
    "chevrolet": ["шевроле"],
    "матиз": ["matiz", "daewoo matiz"],
    "matiz": ["матиз"],
}

CATEGORY_KEYWORDS = {
    "квартира": "nedvizhimost",
    "жилье": "nedvizhimost",
    "дом": "nedvizhimost",
    "машина": "avto",
    "автомобиль": "avto",
    "авто": "avto",
    "матиз": "avto",
    "айфон": "elektronika",
    "iphone": "elektronika",
    "телефон": "elektronika",
    "смартфон": "elektronika",
    "ноутбук": "elektronika",
    "диван": "dlya-doma",
    "куртка": "prodazha",
    "велосипед": "sport",
    "собака": "zhivotnye",
    "кот": "zhivotnye",
    "работа": "rabota",
    "вакансия": "rabota",
}

POPULAR_SUGGESTIONS = [
    "айфон",
    "квартира грозный",
    "матиз",
    "диван",
    "велосипед",
]

REPORT_REASONS = {
    "spam": "Спам",
    "fraud": "Мошенничество",
    "wrong_phone": "Неверный номер телефона",
    "inappropriate": "Недопустимый контент",
    "duplicate": "Дубликат",
    "other": "Другое",
}

MODERATION_REJECT_REASONS = [
    "Неполное описание",
    "Нет цены или она нереалистична",
    "Запрещённый товар или услуга",
    "Контакты в тексте объявления",
    "Дубликат объявления",
    "Фото не соответствуют описанию",
    "Нарушение правил сообщества",
]

REPORT_STATUS_LABELS = {
    "new": "Новая",
    "reviewed": "Рассмотрена",
}

POST_TITLE_MIN_LEN = 5
POST_TITLE_MAX_LEN = 50
POST_BODY_MIN_LEN = 20
POST_BODY_MAX_LEN = 3000

POST_STATUS_LABELS = {
    "draft": "Черновик",
    "pending": "На модерации",
    "published": "Опубликовано",
    "hidden": "Снято с публикации",
    "expired": "Истекло",
    "deleted": "Удалено",
}

REPORTS_AUTO_HIDE_THRESHOLD = 3
