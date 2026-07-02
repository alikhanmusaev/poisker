from datetime import timedelta, timezone

from flask import current_app, session

from app.constants import CATEGORIES, CITIES, POST_BODY_MAX_LEN, POST_BODY_MIN_LEN, POST_TITLE_DB_MAX_LEN, POST_TITLE_MAX_LEN, POST_TITLE_MIN_LEN
from app.extensions import db
from app.models import BlockedPhone, PhoneDailyPublish, Post, utcnow
from app.services.phone import generate_edit_token, hash_phone, mask_phone, validate_phone
from app.services.phone_crypto import decrypt_phone, encrypt_phone
from app.services.ranking import calculate_rank_score, start_of_today_msk, today_msk_date
from app.services.search import index_post, remove_post_from_index
from app.services.slug import make_unique_slug
from app.services.storage import delete_stored_image, delete_stored_images


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


def get_viewable_post(post_id: str, token: str | None = None) -> Post | None:
    """Public posts for everyone; pending/hidden posts for owner with edit token."""
    post = Post.query.filter_by(id=post_id).first()
    if not post or post.status == "deleted":
        return None
    if post.status == "expired" or is_post_expired(post):
        if token and post.edit_token == token:
            return post
        return None
    if is_post_publicly_visible(post):
        return post
    if token and post.edit_token == token and post.status in ("pending", "hidden"):
        return post
    return None


def get_viewable_post_by_slug(
    slug: str,
    *,
    city_slug: str | None = None,
    category_slug: str | None = None,
    token: str | None = None,
) -> Post | None:
    post = get_published_post_by_slug(slug)
    if post:
        return post
    if not token:
        return None
    post = Post.query.filter_by(slug=slug, edit_token=token).first()
    if not post or post.status not in ("pending", "hidden"):
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
    daily = PhoneDailyPublish.query.filter_by(phone_hash=phone_hash, publish_date=today).first()
    if daily:
        if daily.post_id:
            linked = Post.query.filter_by(id=daily.post_id).first()
            if linked is not None:
                return True
        else:
            start = start_of_today_msk()
            active_today = Post.query.filter(
                Post.phone_hash == phone_hash,
                Post.created_at >= start,
                Post.status.in_(["published", "hidden", "pending"]),
            ).first()
            if active_today:
                return True
        db.session.delete(daily)
        db.session.flush()
    start = start_of_today_msk()
    return (
        Post.query.filter(
            Post.phone_hash == phone_hash,
            Post.created_at >= start,
            Post.status.in_(["published", "hidden", "pending", "deleted"]),
        ).first()
        is not None
    )


def release_daily_publish_slot(post: Post) -> None:
    """Release a daily publish slot — not used for normal soft delete flows."""
    today = today_msk_date()
    PhoneDailyPublish.query.filter_by(
        phone_hash=post.phone_hash,
        publish_date=today,
    ).delete(synchronize_session=False)


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


def _validate_post_text(
    title: str,
    body: str,
    *,
    current_title: str | None = None,
    current_body: str | None = None,
) -> tuple[str, str]:
    title = (title or "").strip()
    body = (body or "").strip()
    prev_title = (current_title or "").strip()
    prev_body = (current_body or "").strip()

    if len(title) < POST_TITLE_MIN_LEN:
        raise ValidationError("Заголовок слишком короткий")
    if title != prev_title and len(title) > POST_TITLE_MAX_LEN:
        raise ValidationError(f"Заголовок слишком длинный (макс. {POST_TITLE_MAX_LEN} символов)")
    if len(title) > POST_TITLE_DB_MAX_LEN:
        raise ValidationError(f"Заголовок слишком длинный (макс. {POST_TITLE_DB_MAX_LEN} символов)")

    if len(body) < POST_BODY_MIN_LEN:
        raise ValidationError("Описание слишком короткое")
    if body != prev_body and len(body) > POST_BODY_MAX_LEN:
        raise ValidationError(f"Описание слишком длинное (макс. {POST_BODY_MAX_LEN} символов)")

    return title, body


def create_post(data: dict, ip_hash: str | None = None, *, publish: bool = False) -> Post:
    if data.get("city") not in CITIES:
        raise ValidationError("Выберите город из списка")
    if data.get("category") not in CATEGORIES:
        raise ValidationError("Выберите категорию")

    title, body = _validate_post_text(data.get("title", ""), data.get("body", ""))
    seller_name = _validate_seller_name(data.get("seller_name"))

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
        status="published" if publish else "pending",
        images=images,
        ip_hash=ip_hash,
        has_photo=bool(images),
        cover_index=int(data.get("cover_index", 0) or 0),
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
    if publish:
        index_post(post)
    return post


def get_post_by_token(post_id: str, token: str) -> Post | None:
    return (
        Post.query.filter_by(id=post_id, edit_token=token)
        .filter(Post.status != "deleted")
        .first()
    )


def reveal_post_phone(post: Post) -> str | None:
    return decrypt_phone(post.phone_encrypted)


def update_post(post: Post, data: dict) -> Post:
    if data.get("category") not in CATEGORIES:
        raise ValidationError("Выберите категорию")
    if data.get("city") not in CITIES:
        raise ValidationError("Выберите город из списка")

    title, body = _validate_post_text(
        data.get("title", ""),
        data.get("body", ""),
        current_title=post.title,
        current_body=post.body,
    )
    seller_name = _validate_seller_name(data.get("seller_name"))

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

    images = list(data.get("images") if data.get("images") is not None else (post.images or []))
    cover_index = int(data.get("cover_index", getattr(post, "cover_index", 0) or 0))
    if images:
        cover_index = min(max(cover_index, 0), len(images) - 1)
    else:
        cover_index = 0

    live_images = list(post.images or [])
    live_cover = getattr(post, "cover_index", 0) or 0
    sensitive_changed = (
        title != post.title
        or body != post.body
        or images != live_images
        or cover_index != live_cover
    )

    post.seller_name = seller_name
    post.category = data["category"]
    post.city = data["city"]
    post.price = price

    if sensitive_changed:
        post.pending_revision = {
            "title": title,
            "body": body,
            "images": images,
            "cover_index": cover_index,
            "submitted_at": utcnow().isoformat(),
        }

    post.rank_score = calculate_rank_score(post)
    post.updated_at = utcnow()
    db.session.commit()
    if post.status == "published" and not is_post_expired(post):
        index_post(post)
    elif post.status != "published":
        remove_post_from_index(post.id)
    return post


def apply_pending_revision(post: Post) -> bool:
    revision = post.pending_revision
    if not revision:
        return False

    old_images = set(post.images or [])
    new_images = list(revision.get("images", post.images or []))
    title_changed = revision.get("title", post.title) != post.title

    post.title = revision.get("title", post.title)
    post.body = revision.get("body", post.body)
    post.images = new_images
    post.cover_index = int(revision.get("cover_index", 0) or 0)
    post.has_photo = bool(new_images)
    post.pending_revision = None

    if title_changed:
        post.slug = make_unique_slug(post.title, post.id, current_slug=post.slug)

    removed = old_images - set(new_images)
    if removed:
        delete_stored_images(list(removed))

    post.rank_score = calculate_rank_score(post)
    post.updated_at = utcnow()
    db.session.commit()
    if post.status == "published" and not is_post_expired(post):
        index_post(post)
    return True


def reject_pending_revision(post: Post) -> bool:
    revision = post.pending_revision
    if not revision:
        return False

    live_images = set(post.images or [])
    pending_images = set(revision.get("images", []))
    for url in pending_images - live_images:
        delete_stored_image(url)

    post.pending_revision = None
    post.updated_at = utcnow()
    db.session.commit()
    return True


def delete_post(post: Post):
    remove_post_from_index(post.id)
    post.status = "deleted"
    now = utcnow()
    post.deleted_at = now
    post.updated_at = now
    db.session.commit()


def hard_delete_post(post: Post):
    """Physical delete — not used in normal user/admin flows."""
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
