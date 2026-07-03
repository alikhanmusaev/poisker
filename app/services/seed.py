"""Демо-объявления для разработки и скриншотов Google Play."""

from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models import Post, utcnow
from app.services.phone import generate_edit_token, hash_phone, mask_phone, validate_phone
from app.services.phone_crypto import encrypt_phone
from app.services.ranking import calculate_rank_score
from app.services.search import index_post, remove_post_from_index
from app.services.slug import make_unique_slug

SEED_MARKER = "seed-demo"


def demo_image_for(category: str) -> list[str]:
    return [f"/static/demo/{category}.jpg"]


SAMPLE_POSTS = [
    {
        "title": "2-к квартира, пр. Путина",
        "body": "Просторная двухкомнатная квартира в центре Грозного. Ремонт, мебель по договорённости. Документы в порядке, один собственник.",
        "category": "nedvizhimost",
        "city": "grozny",
        "price": 4_500_000,
        "phone": "+79001110001",
        "days_ago": 1,
        "views": 124,
    },
    {
        "title": "Toyota Camry 2018, 2.5 AT",
        "body": "Автомобиль в отличном состоянии, полная история обслуживания. Без ДТП, родной пробег 87 000 км. Торг уместен.",
        "category": "avto",
        "city": "grozny",
        "price": 1_850_000,
        "phone": "+79001110002",
        "days_ago": 2,
        "views": 89,
    },
    {
        "title": "iPhone 14 Pro 256 ГБ",
        "body": "Смартфон в идеале, комплект полный. Аккумулятор 91%. Покупался в официальном магазине, чек сохранён.",
        "category": "elektronika",
        "city": "gudermes",
        "price": 75_000,
        "phone": "+79001110003",
        "days_ago": 0,
        "views": 56,
    },
    {
        "title": "Угловой диван, б/у",
        "body": "Диван раскладной, ткань чистая без пятен. Самовывоз из Аргуна. Размеры по запросу в сообщениях по телефону.",
        "category": "dlya-doma",
        "city": "argun",
        "price": 25_000,
        "phone": "+79001110004",
        "days_ago": 3,
        "views": 34,
    },
    {
        "title": "Ремонт квартир под ключ",
        "body": "Опыт более 10 лет. Штукатурка, плитка, электрика, сантехника. Бесплатный выезд и смета по Грозному и пригороду.",
        "category": "uslugi",
        "city": "grozny",
        "price": None,
        "phone": "+79001110005",
        "days_ago": 4,
        "views": 41,
    },
    {
        "title": "Продавец в продуктовый магазин",
        "body": "Требуется ответственный продавец на полный день. Официальное оформление, стабильная зарплата, обучение на месте.",
        "category": "rabota",
        "city": "urus-martan",
        "price": 45_000,
        "phone": "+79001110006",
        "days_ago": 5,
        "views": 67,
    },
    {
        "title": "Щенки немецкой овчарки",
        "body": "Щенки от родителей с документами, привиты по возрасту. Помощь с содержанием и советы по воспитанию.",
        "category": "zhivotnye",
        "city": "shali",
        "price": 15_000,
        "phone": "+79001110007",
        "days_ago": 2,
        "views": 112,
    },
    {
        "title": "Кроссовки Nike, 42 размер",
        "body": "Оригинал, носили пару раз. Коробка и бирки на месте. Цвет чёрный/белый, подойдут для зала и повседневной носки.",
        "category": "prodazha",
        "city": "grozny",
        "price": 5_500,
        "phone": "+79001110008",
        "days_ago": 1,
        "views": 23,
    },
    {
        "title": "Бензопила Stihl MS 180",
        "body": "Рабочая пила, недавно обслуживалась. Идеально для заготовки дров и работ на участке. Масло в комплекте.",
        "category": "stroitelstvo",
        "city": "kurchaloy",
        "price": 12_000,
        "phone": "+79001110009",
        "days_ago": 6,
        "views": 19,
    },
    {
        "title": "Детская коляска 3 в 1",
        "body": "Коляска трансформер, все режимы исправны. Лёгкая, удобно складывается. Состояние хорошее, чистая.",
        "category": "detskie",
        "city": "naurskaya",
        "price": 8_000,
        "phone": "+79001110010",
        "days_ago": 7,
        "views": 45,
    },
    {
        "title": "Запчасти на ВАЗ 2114",
        "body": "Продам набор запчастей: генератор, стартер, амортизаторы передние. Всё снято с рабочей машины, можно по отдельности.",
        "category": "zapchasti",
        "city": "grozny",
        "price": 3_000,
        "phone": "+79001110011",
        "days_ago": 3,
        "views": 28,
    },
    {
        "title": "Свежие овощи с огорода",
        "body": "Помидоры, огурцы, зелень — урожай этого сезона. Доставка по Шатою и ближайшим сёлам, опт и розница.",
        "category": "produkti",
        "city": "shatoy",
        "price": 500,
        "phone": "+79001110012",
        "days_ago": 0,
        "views": 15,
    },
    {
        "title": "Магазин одежды — готовый бизнес",
        "body": "Действующий магазин в проходном месте, аренда согласована. Товарный остаток, вывеска, клиентская база.",
        "category": "biznes",
        "city": "grozny",
        "price": 800_000,
        "phone": "+79001110013",
        "days_ago": 8,
        "views": 73,
        "contact_clicks": 5,
    },
    {
        "title": "Горный велосипед 26″",
        "body": "Велосипед на 21 скорости, тормоза дисковые. Подойдёт для города и лёгких трасс. Недавно смазан и отрегулирован.",
        "category": "sport",
        "city": "achkhoy-martan",
        "price": 18_000,
        "phone": "+79001110014",
        "days_ago": 4,
        "views": 31,
    },
    {
        "title": "Фикус и монстера в горшках",
        "body": "Комнатные растения для дома и офиса. Высота от 40 до 90 см. Помогу с пересадкой и советами по уходу.",
        "category": "rasteniya",
        "city": "shelkovskaya",
        "price": 1_200,
        "phone": "+79001110015",
        "days_ago": 2,
        "views": 12,
    },
    {
        "title": "Сдам гараж на длительный срок",
        "body": "Охраняемая территория, удобный подъезд. Подойдёт для легкового авто или хранения. Оплата помесячно.",
        "category": "drugoe",
        "city": "goyty",
        "price": 5_000,
        "phone": "+79001110016",
        "days_ago": 5,
        "views": 22,
    },
]


def is_seeded() -> bool:
    return Post.query.filter_by(ip_hash=SEED_MARKER).first() is not None


def clear_seed_posts() -> int:
    posts = Post.query.filter_by(ip_hash=SEED_MARKER).all()
    for post in posts:
        remove_post_from_index(post.id)
        db.session.delete(post)
    db.session.commit()
    return len(posts)


def _create_seed_post(data: dict) -> Post:
    phone = validate_phone(data["phone"])
    phone_hash = hash_phone(phone)
    now = utcnow()
    days_ago = data.get("days_ago", 0)
    created_at = now - timedelta(days=days_ago, hours=days_ago * 2)
    expiry_days = current_app.config["POST_EXPIRY_DAYS"]
    images = data.get("images") or demo_image_for(data["category"])

    post = Post(
        title=data["title"],
        seller_name=data.get("seller_name", "Продавец"),
        body=data["body"],
        category=data["category"],
        city=data["city"],
        price=data.get("price"),
        phone_hash=phone_hash,
        phone_masked=mask_phone(phone),
        phone_encrypted=encrypt_phone(phone),
        edit_token=generate_edit_token(),
        status="published",
        images=images,
        ip_hash=SEED_MARKER,
        views=data.get("views", 0),
        contact_clicks=data.get("contact_clicks", 0),
        has_photo=bool(images),
        created_at=created_at,
        expires_at=created_at + timedelta(days=expiry_days),
        bumped_at=created_at,
    )
    post.rank_score = calculate_rank_score(post)
    db.session.add(post)
    db.session.flush()
    post.slug = make_unique_slug(post.title, post.id)
    db.session.commit()
    index_post(post)
    return post


def refresh_seed_images() -> int:
    """Добавить демо-фото к уже созданным тестовым объявлениям."""
    updated_posts = []
    for post in Post.query.filter_by(ip_hash=SEED_MARKER).all():
        if post.images:
            continue
        post.images = demo_image_for(post.category)
        post.has_photo = True
        post.rank_score = calculate_rank_score(post)
        updated_posts.append(post)
    if updated_posts:
        db.session.commit()
        for post in updated_posts:
            index_post(post)
    return len(updated_posts)


def seed_demo_posts(*, force: bool = False) -> int:
    """Создать демо-объявления. Возвращает число созданных записей."""
    if is_seeded():
        if not force:
            return 0
        clear_seed_posts()

    created = 0
    for item in SAMPLE_POSTS:
        _create_seed_post(item)
        created += 1
    return created
