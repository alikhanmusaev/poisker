from app.data.chechnya_settlements import CHECHNYA_SETTLEMENTS

CITIES = CHECHNYA_SETTLEMENTS

# Предложный падеж для SEO-заголовков («в Грозном»)
CITY_LOCATIVE = {
    "grozny": "Грозном",
    "gudermes": "Гудермесе",
    "argun": "Аргуне",
    "urus-martan": "Урус-Мартане",
    "shali": "Шали",
    "kurchaloy": "Курчалое",
    "naurskaya": "Наурской",
    "vedeno": "Ведено",
    "shatoy": "Шатое",
    "nozhay-yurt": "Ножай-Юрте",
    "shelkovskaya": "Шелковской",
    "goyty": "Гойтах",
    "achkhoy-martan": "Ачхой-Мартане",
    "tsentoroy": "Центорое",
    "starye-atagi": "Старых Атагах",
    "katar-yurt": "Катар-Юрте",
    "gekhi": "Гехи",
    "samashki": "Самашках",
    "alleroi": "Аллерое",
    "benoy": "Беное",
}

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
CATEGORY_ICONS = {slug: icon for slug, (_, icon) in CATEGORIES.items()}

SORT_OPTIONS = {
    "rank": "Рекомендуемые",
    "relevance": "По релевантности",
    "date_desc": "Сначала новые",
    "price_asc": "Сначала дешевле",
    "price_desc": "Сначала дороже",
}

DEFAULT_SORT = "rank"
DEFAULT_SEARCH_SORT = "relevance"

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

REPORT_STATUS_LABELS = {
    "new": "Новая",
    "reviewed": "Рассмотрена",
}

POST_STATUSES = ("draft", "pending", "published", "hidden", "expired", "deleted")

POST_TITLE_MIN_LEN = 5
POST_TITLE_MAX_LEN = 70
POST_BODY_MIN_LEN = 20
POST_BODY_MAX_LEN = 3000
POST_TITLE_DB_MAX_LEN = 200

POST_STATUS_LABELS = {
    "draft": "Черновик",
    "pending": "На модерации",
    "published": "Опубликовано",
    "hidden": "Скрыто",
    "expired": "Истекло",
    "deleted": "Удалено",
}

PROMOTION_TYPES = {
    "boost_24h": ("Поднять на 24 часа", 1.5, 24),
    "top_7d": ("Топ 7 дней", 2.0, 168),
}

REPORTS_AUTO_HIDE_THRESHOLD = 3
