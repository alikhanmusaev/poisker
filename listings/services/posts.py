import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.phone import normalize_phone
from listings.constants import CATEGORIES, CITIES, CONDITION_LABELS, POST_BODY_MAX_LEN, POST_BODY_MIN_LEN, POST_TITLE_MAX_LEN, POST_TITLE_MIN_LEN
from listings.models import Post
from locations.models import Settlement


class ValidationError(Exception):
    pass


def _validate_text(title: str, body: str):
    title = (title or "").strip()
    body = (body or "").strip()
    if len(title) < POST_TITLE_MIN_LEN or len(title) > POST_TITLE_MAX_LEN:
        raise ValidationError(f"Заголовок: от {POST_TITLE_MIN_LEN} до {POST_TITLE_MAX_LEN} символов.")
    if len(body) < POST_BODY_MIN_LEN or len(body) > POST_BODY_MAX_LEN:
        raise ValidationError(f"Описание: от {POST_BODY_MIN_LEN} до {POST_BODY_MAX_LEN} символов.")
    return title, body


def _resolve_settlement(settlement_id, city: str = "") -> Settlement:
    try:
        settlement_id = int(settlement_id)
    except (TypeError, ValueError):
        settlement_id = None
    settlements = Settlement.objects.filter(is_active=True, region__is_active=True)
    if settlement_id:
        settlement = settlements.filter(pk=settlement_id).first()
    elif city in CITIES:
        settlement = settlements.filter(slug=city, region__code="12").first()
    else:
        settlement = None
    if settlement is None:
        raise ValidationError("Выберите населённый пункт из подсказок.")
    return settlement


def _validate_category_city(category: str, city: str, settlement_id):
    if category not in CATEGORIES:
        raise ValidationError("Выберите категорию.")
    settlement = _resolve_settlement(settlement_id, city)
    return category, settlement.slug, settlement


def _normalize_phone(phone: str) -> str:
    return normalize_phone(phone)


def _seller_phone(user, *, required: bool = True) -> str:
    phone = _normalize_phone(user.phone or "")
    if not phone or len(re.sub(r"\D", "", phone)) < 10:
        if required:
            raise ValidationError("Укажите телефон в профиле.")
        return ""
    return phone


def sync_user_post_phones(user) -> int:
    phone = _seller_phone(user)
    return Post.objects.filter(user=user).update(contact_phone=phone)


from listings.services.ranking import calculate_rank_score
from listings.services.search import index_post
from listings.services.seo_urls import make_seo_slug


def _draft_title(title: str) -> str:
    title = (title or "").strip()
    if not title:
        return "Черновик"
    return title[:POST_TITLE_MAX_LEN]


def _default_draft_settlement() -> Settlement | None:
    return (
        Settlement.objects.filter(region__code="12", is_active=True)
        .filter(Q(slug="grozny") | Q(name__iexact="Грозный"))
        .select_related("region")
        .order_by("-population", "name")
        .first()
        or Settlement.objects.filter(region__code="12", is_active=True)
        .select_related("region")
        .order_by("-population", "name")
        .first()
    )


def _draft_category_city(category: str, city: str, settlement_id):
    if category not in CATEGORIES:
        category = "drugoe"
    try:
        settlement = _resolve_settlement(settlement_id, city)
    except ValidationError:
        settlement = _default_draft_settlement()
    if settlement is not None:
        return category, settlement.slug, settlement
    if city not in CITIES:
        city = next(iter(CITIES))
    return category, city, None


def _normalize_price(price):
    if price in (None, ""):
        return None
    try:
        value = int(price)
    except (TypeError, ValueError):
        return None
    return None if value < 0 else value


def _normalize_condition(value) -> str:
    return value if value in CONDITION_LABELS else "used"


def can_edit_rejected_post(post: Post) -> bool:
    """Rejected pre-publication listings may be edited and resubmitted."""
    return post.status == "hidden" and not post.ever_published


@transaction.atomic
def create_post(user, data: dict, *, image_keys: list | None = None, as_draft: bool = False) -> Post:
    if user.is_blocked:
        raise ValidationError("Аккаунт заблокирован.")

    if as_draft:
        title = _draft_title(data.get("title"))
        body = (data.get("body") or "").strip()[:POST_BODY_MAX_LEN]
        category, city, settlement = _draft_category_city(
            data.get("category") or "", data.get("city") or "", data.get("settlement_id")
        )
        status = "draft"
    else:
        title, body = _validate_text(data.get("title"), data.get("body"))
        category, city, settlement = _validate_category_city(
            data.get("category"), data.get("city"), data.get("settlement_id")
        )
        status = "pending"

    price = _normalize_price(data.get("price"))
    condition = _normalize_condition(data.get("condition"))

    contact_phone = _seller_phone(user, required=not as_draft)

    images = image_keys or []
    cover_index = min(max(int(data.get("cover_index") or 0), 0), max(len(images) - 1, 0))

    post = Post(
        user=user,
        title=title,
        body=body,
        category=category,
        city=city,
        settlement=settlement,
        condition=condition,
        price=price,
        contact_phone=contact_phone,
        status=status,
        images=images,
        cover_index=cover_index,
        has_photo=bool(images),
        expires_at=timezone.now() + timedelta(days=settings.POST_EXPIRY_DAYS),
    )
    post.slug = make_seo_slug(title, city)
    post.rank_score = calculate_rank_score(post)
    post.save()
    return post


@transaction.atomic
def update_post(post: Post, user, data: dict, *, as_draft: bool = False, image_keys: list | None = None) -> Post:
    if post.user_id != user.id:
        raise ValidationError("Нет доступа.")
    if post.status == "deleted":
        raise ValidationError("Объявление удалено.")
    if post.status == "hidden" and not can_edit_rejected_post(post):
        raise ValidationError("Снятое объявление нельзя редактировать. Опубликуйте его снова.")
    if post.status == "expired":
        raise ValidationError("Истёкшее объявление нельзя редактировать. Отправьте его на модерацию снова.")

    if as_draft:
        if post.status != "draft":
            raise ValidationError("В черновик можно сохранить только черновик.")
        title = _draft_title(data.get("title"))
        body = (data.get("body") or "").strip()[:POST_BODY_MAX_LEN]
        category, city, settlement = _draft_category_city(
            data.get("category") or "", data.get("city") or "", data.get("settlement_id")
        )
        price = _normalize_price(data.get("price"))
        condition = _normalize_condition(data.get("condition"))
        contact_phone = _seller_phone(user, required=False)
        post.title = title
        post.body = body
        post.category = category
        post.city = city
        post.settlement = settlement
        post.condition = condition
        post.price = price
        post.contact_phone = contact_phone
        post.status = "draft"
        post.pending_revision = None
        post.slug = make_seo_slug(title, city)
        post.updated_at = timezone.now()
        if image_keys is not None:
            cover_index = min(max(int(data.get("cover_index") or 0), 0), max(len(image_keys) - 1, 0))
            post.images = image_keys
            post.cover_index = cover_index
            post.has_photo = bool(image_keys)
        post.rank_score = calculate_rank_score(post)
        post.save()
        return post

    title, body = _validate_text(data.get("title"), data.get("body"))
    category, city, settlement = _validate_category_city(
        data.get("category"), data.get("city"), data.get("settlement_id")
    )
    price = _normalize_price(data.get("price"))
    condition = _normalize_condition(data.get("condition"))

    contact_phone = _seller_phone(user)
    old_price = post.price
    was_published = post.status == "published"

    sensitive_changed = title != post.title or body != post.body
    meta_changed = (
        category != post.category
        or city != post.city
        or settlement.id != post.settlement_id
        or price != post.price
        or condition != post.condition
    )

    post.contact_phone = contact_phone
    post.updated_at = timezone.now()

    if was_published and (sensitive_changed or meta_changed):
        post.pending_revision = {
            "title": title,
            "body": body,
            "category": category,
            "city": city,
            "settlement_id": settlement.id,
            "condition": condition,
            "price": price,
        }
    else:
        post.title = title
        post.body = body
        post.category = category
        post.city = city
        post.settlement = settlement
        post.condition = condition
        post.price = price
        post.pending_revision = None
        if sensitive_changed or meta_changed:
            post.slug = make_seo_slug(title, city)

    if post.status == "draft":
        post.status = "pending"
        post.title = title
        post.body = body
        post.category = category
        post.city = city
        post.settlement = settlement
        post.condition = condition
        post.price = price
        post.pending_revision = None
        post.slug = make_seo_slug(title, city)
    elif can_edit_rejected_post(post):
        post.status = "pending"
        post.title = title
        post.body = body
        post.category = category
        post.city = city
        post.settlement = settlement
        post.condition = condition
        post.price = price
        post.pending_revision = None
        post.moderation_note = ""
        post.slug = make_seo_slug(title, city)

    if image_keys is not None:
        cover_index = min(max(int(data.get("cover_index") or 0), 0), max(len(image_keys) - 1, 0))
        post.images = image_keys
        post.cover_index = cover_index
        post.has_photo = bool(image_keys)

    post.rank_score = calculate_rank_score(post)
    post.save()

    if was_published and old_price != price and not (sensitive_changed or meta_changed):
        from bookmarks.services import notify_price_changed

        notify_price_changed(post, old_price, price)
    return post


@transaction.atomic
def submit_draft(post: Post, user) -> Post:
    """Send draft to moderation with full validation of current fields."""
    if post.user_id != user.id and not user.is_staff:
        raise ValidationError("Нет доступа.")
    if post.status != "draft":
        raise ValidationError("Отправить на модерацию можно только черновик.")
    if user.is_blocked:
        raise ValidationError("Аккаунт заблокирован.")

    title, body = _validate_text(post.title, post.body)
    category, city, settlement = _validate_category_city(
        post.category, post.city, post.settlement_id
    )
    post.title = title
    post.body = body
    post.category = category
    post.city = city
    post.settlement = settlement
    post.status = "pending"
    post.pending_revision = None
    post.updated_at = timezone.now()
    post.slug = make_seo_slug(title, city)
    post.rank_score = calculate_rank_score(post)
    post.save()
    return post


@transaction.atomic
def unpublish_post(post: Post, user) -> None:
    if post.user_id != user.id and not user.is_staff:
        raise ValidationError("Нет доступа.")
    if post.status != "published":
        raise ValidationError("Можно снять с публикации только опубликованное объявление.")
    post.status = "hidden"
    post.updated_at = timezone.now()
    post.save(update_fields=["status", "updated_at"])
    from bookmarks.services import notify_post_unpublished

    notify_post_unpublished(post)


@transaction.atomic
def republish_post(post: Post, user) -> Post:
    """Send hidden/expired listing back to moderation (pending)."""
    if post.user_id != user.id and not user.is_staff:
        raise ValidationError("Нет доступа.")
    if post.status not in ("hidden", "expired"):
        raise ValidationError("Можно отправить на модерацию только снятое или истёкшее объявление.")
    if user.is_blocked:
        raise ValidationError("Аккаунт заблокирован.")
    now = timezone.now()
    if post.expires_at <= now:
        post.expires_at = now + timedelta(days=settings.POST_EXPIRY_DAYS)
    post.status = "pending"
    post.pending_revision = None
    post.updated_at = now
    post.rank_score = calculate_rank_score(post)
    post.save(
        update_fields=["status", "pending_revision", "expires_at", "updated_at", "rank_score"]
    )
    return post


@transaction.atomic
def delete_post(post: Post, user) -> None:
    if post.user_id != user.id and not user.is_staff:
        raise ValidationError("Нет доступа.")
    if post.ever_published and not user.is_staff:
        raise ValidationError(
            "Объявление, которое хотя бы раз публиковалось, нельзя удалить. "
            "Его можно только снять с публикации."
        )
    if post.status == "published":
        raise ValidationError("Опубликованное объявление нельзя удалить. Снимите его с публикации.")
    if post.status == "deleted":
        raise ValidationError("Объявление уже удалено.")
    was_visible = post.status in ("published", "hidden", "expired")
    post.status = "deleted"
    post.deleted_at = timezone.now()
    post.updated_at = timezone.now()
    post.save(update_fields=["status", "deleted_at", "updated_at"])
    if was_visible:
        from bookmarks.services import notify_post_unpublished

        notify_post_unpublished(post)
