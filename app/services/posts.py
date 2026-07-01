from datetime import timedelta, timezone

from flask import current_app, session

from app.constants import CATEGORIES, CITIES
from app.extensions import db
from app.models import BlockedPhone, PhoneDailyPublish, Post, utcnow
from app.services.phone import generate_edit_token, hash_phone, mask_phone, validate_phone
from app.services.phone_crypto import decrypt_phone, encrypt_phone
from app.services.ranking import calculate_rank_score, start_of_today_msk, today_msk_date
from app.services.search import index_post, remove_post_from_index
from app.services.slug import make_unique_slug
from app.services.storage import delete_stored_images


def _normalize_expires_at(expires_at):
    if not expires_at:
        return None
    if expires_at.tzinfo is None:
        return expires_at.replace(tzinfo=timezone.utc)
    return expires_at


def is_post_expired(post: Post) -> bool:
    expires_at = _normalize_expires_at(post.expires_at)
    return bool(expires_at and expires_at < utcnow())


def is_post_publicly_visible(post: Post) -> bool:
    if post.status != "published":
        return False
    return not is_post_expired(post)


def mark_post_expired_if_needed(post: Post) -> bool:
    """Return True if post remains publicly visible."""
    if post.status != "published":
        return False
    if not is_post_expired(post):
        return True
    post.status = "expired"
    remove_post_from_index(post.id)
    db.session.commit()
    return False


def get_published_post_by_slug(slug: str) -> Post | None:
    post = Post.query.filter_by(slug=slug, status="published").first()
    if not post:
        return None
    if not mark_post_expired_if_needed(post):
        return None
    return post


def get_public_post(post_id: str) -> Post | None:
    post = Post.query.filter_by(id=post_id, status="published").first()
    if not post:
        return None
    if not mark_post_expired_if_needed(post):
        return None
    return post


class PostLimitError(Exception):
    pass


class BlockedPhoneError(Exception):
    pass


class ValidationError(Exception):
    pass


def has_post_today(phone_hash: str) -> bool:
    today = today_msk_date()
    if PhoneDailyPublish.query.filter_by(phone_hash=phone_hash, publish_date=today).first():
        return True
    start = start_of_today_msk()
    return (
        Post.query.filter(
            Post.phone_hash == phone_hash,
            Post.created_at >= start,
            Post.status.in_(["published", "hidden"]),
        ).first()
        is not None
    )


def record_phone_publish(phone_hash: str, post_id: str):
    today = today_msk_date()
    existing = PhoneDailyPublish.query.filter_by(phone_hash=phone_hash, publish_date=today).first()
    if existing:
        return
    db.session.add(
        PhoneDailyPublish(
            phone_hash=phone_hash,
            publish_date=today,
            post_id=post_id,
        )
    )


def is_phone_blocked(phone_hash: str) -> bool:
    return BlockedPhone.query.filter_by(phone_hash=phone_hash).first() is not None


def _validate_seller_name(value: str | None) -> str:
    seller_name = (value or "").strip()
    if len(seller_name) < 2:
        raise ValidationError("Укажите имя")
    if len(seller_name) > 80:
        raise ValidationError("Имя слишком длинное")
    return seller_name


def create_post(data: dict, ip_hash: str | None = None) -> Post:
    if data.get("city") not in CITIES:
        raise ValidationError("Выберите город из списка")
    if data.get("category") not in CATEGORIES:
        raise ValidationError("Выберите категорию")

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    seller_name = _validate_seller_name(data.get("seller_name"))
    if len(title) < 5:
        raise ValidationError("Заголовок слишком короткий")
    if len(body) < 20:
        raise ValidationError("Описание слишком короткое")

    phone = validate_phone(data.get("phone", ""))
    phone_hash = hash_phone(phone)

    if is_phone_blocked(phone_hash):
        raise BlockedPhoneError("Этот номер заблокирован")

    if has_post_today(phone_hash):
        raise PostLimitError("С этого номера сегодня уже опубликовано объявление")

    price = data.get("price")
    if price is not None and price != "":
        try:
            price = int(price)
            if price < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError("Некорректная цена")
    else:
        price = None

    images = data.get("images") or []
    expiry_days = current_app.config["POST_EXPIRY_DAYS"]
    now = utcnow()

    post = Post(
        title=title,
        seller_name=seller_name,
        body=body,
        category=data["category"],
        city=data["city"],
        price=price,
        phone_hash=phone_hash,
        phone_masked=mask_phone(phone),
        phone_encrypted=encrypt_phone(phone),
        edit_token=generate_edit_token(),
        status="published",
        images=images,
        ip_hash=ip_hash,
        has_photo=bool(images),
        created_at=now,
        expires_at=now + timedelta(days=expiry_days),
        bumped_at=now,
    )
    db.session.add(post)
    db.session.flush()
    post.slug = make_unique_slug(title, post.id)
    post.rank_score = calculate_rank_score(post)
    record_phone_publish(phone_hash, post.id)
    db.session.commit()
    index_post(post)
    return post


def get_post_by_token(post_id: str, token: str) -> Post | None:
    return Post.query.filter_by(id=post_id, edit_token=token).first()


def reveal_post_phone(post: Post) -> str | None:
    return decrypt_phone(post.phone_encrypted)


def update_post(post: Post, data: dict) -> Post:
    if data.get("category") not in CATEGORIES:
        raise ValidationError("Выберите категорию")
    if data.get("city") not in CITIES:
        raise ValidationError("Выберите город из списка")

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    seller_name = _validate_seller_name(data.get("seller_name"))
    if len(title) < 5:
        raise ValidationError("Заголовок слишком короткий")
    if len(body) < 20:
        raise ValidationError("Описание слишком короткое")

    price = data.get("price")
    if price is not None and price != "":
        try:
            price = int(price)
            if price < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValidationError("Некорректная цена")
    else:
        price = None

    images = data.get("images")
    title_changed = title != post.title
    city_changed = data["city"] != post.city
    post.title = title
    post.seller_name = seller_name
    post.body = body
    post.category = data["category"]
    post.city = data["city"]
    post.price = price
    if title_changed:
        post.slug = make_unique_slug(title, post.id, current_slug=post.slug)
    if images is not None:
        removed = set(post.images or []) - set(images)
        if removed:
            delete_stored_images(list(removed))
        post.images = images
        post.has_photo = bool(images)

    post.rank_score = calculate_rank_score(post)
    db.session.commit()
    if post.status == "published" and not is_post_expired(post):
        index_post(post)
    return post


def delete_post(post: Post):
    remove_post_from_index(post.id)
    delete_stored_images(post.images or [])
    db.session.delete(post)
    db.session.commit()


def increment_views(post: Post):
    viewed = session.get("viewed_posts") or []
    if post.id in viewed:
        return
    post.views = (post.views or 0) + 1
    db.session.commit()
    session["viewed_posts"] = (viewed + [post.id])[-200:]


def increment_contact_clicks(post: Post):
    clicked = session.get("contacted_posts") or []
    if post.id in clicked:
        return
    post.contact_clicks = (post.contact_clicks or 0) + 1
    post.rank_score = calculate_rank_score(post)
    db.session.commit()
    session["contacted_posts"] = (clicked + [post.id])[-200:]


def get_feed(city: str | None = None, category: str | None = None, page: int = 1, per_page: int = 20):
    now = utcnow()
    q = Post.query.filter_by(status="published").filter(Post.expires_at >= now)
    if city and city in CITIES:
        q = q.filter_by(city=city)
    if category and category in CATEGORIES:
        q = q.filter_by(category=category)
    q = q.order_by(Post.rank_score.desc(), Post.created_at.desc())
    return q.paginate(page=page, per_page=per_page, error_out=False)
