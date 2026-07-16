from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

from bookmarks.models import CategoryBookmark, Notification, PostBookmark
from listings.constants import CATEGORIES, CATEGORY_LABELS


def unread_notifications_count(user) -> int:
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def is_post_bookmarked(user, post) -> bool:
    if not user.is_authenticated:
        return False
    return PostBookmark.objects.filter(user=user, post=post).exists()


def bookmarked_post_ids_for(user, post_ids) -> set:
    """Return a set of post UUIDs among `post_ids` that the user has bookmarked."""
    if not user.is_authenticated or not post_ids:
        return set()
    return set(
        PostBookmark.objects.filter(user=user, post_id__in=post_ids).values_list("post_id", flat=True)
    )


def is_category_bookmarked(user, category: str) -> bool:
    if not user.is_authenticated:
        return False
    return CategoryBookmark.objects.filter(user=user, category=category).exists()


def toggle_post_bookmark(user, post) -> bool:
    """Return True if now bookmarked, False if removed."""
    deleted, _ = PostBookmark.objects.filter(user=user, post=post).delete()
    if deleted:
        return False
    try:
        PostBookmark.objects.create(user=user, post=post)
    except IntegrityError:
        return True
    return True


def toggle_category_bookmark(user, category: str) -> bool:
    if category not in CATEGORIES:
        raise ValueError("Неизвестная категория.")
    deleted, _ = CategoryBookmark.objects.filter(user=user, category=category).delete()
    if deleted:
        return False
    try:
        CategoryBookmark.objects.create(user=user, category=category)
    except IntegrityError:
        return True
    return True


def mark_notification_read(notification: Notification, user) -> None:
    if notification.user_id != user.id:
        return
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])


def mark_all_notifications_read(user) -> int:
    return Notification.objects.filter(user=user, read_at__isnull=True).update(read_at=timezone.now())


def delete_notification(notification: Notification, user) -> bool:
    if notification.user_id != user.id:
        return False
    notification.delete()
    return True


def delete_all_notifications(user) -> int:
    count, _ = Notification.objects.filter(user=user).delete()
    return count


def _recent_duplicate(user_id, kind: str, *, post_id=None, category: str = "") -> bool:
    since = timezone.now() - timedelta(minutes=1)
    qs = Notification.objects.filter(user_id=user_id, kind=kind, created_at__gte=since)
    if post_id is not None:
        qs = qs.filter(post_id=post_id)
    if category:
        qs = qs.filter(category=category)
    return qs.exists()


def _format_price(value) -> str:
    if value is None:
        return "не указана"
    return f"{int(value):,}".replace(",", " ") + " ₽"


def _create_for_users(user_ids, *, kind, title, body, post=None, category="", payload=None) -> int:
    payload = payload or {}
    created = 0
    author_id = post.user_id if post is not None else None
    for user_id in user_ids:
        if author_id is not None and user_id == author_id:
            continue
        if _recent_duplicate(user_id, kind, post_id=getattr(post, "pk", None), category=category):
            continue
        Notification.objects.create(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            post=post,
            category=category,
            payload=payload,
        )
        created += 1
    return created


def notify_price_changed(post, old_price, new_price) -> int:
    if old_price == new_price:
        return 0
    user_ids = list(
        PostBookmark.objects.filter(post=post).values_list("user_id", flat=True)
    )
    return _create_for_users(
        user_ids,
        kind=Notification.KIND_PRICE_CHANGED,
        title="Изменилась цена",
        body=f"«{post.title}»: {_format_price(old_price)} → {_format_price(new_price)}",
        post=post,
        payload={"old_price": old_price, "new_price": new_price},
    )


def notify_post_unpublished(post) -> int:
    user_ids = list(
        PostBookmark.objects.filter(post=post).values_list("user_id", flat=True)
    )
    return _create_for_users(
        user_ids,
        kind=Notification.KIND_POST_UNPUBLISHED,
        title="Объявление снято",
        body=f"«{post.title}» больше не опубликовано.",
        post=post,
    )


def notify_category_new_post(post) -> int:
    if post.status != "published":
        return 0
    user_ids = list(
        CategoryBookmark.objects.filter(category=post.category).values_list("user_id", flat=True)
    )
    category_label = CATEGORY_LABELS.get(post.category, post.category)
    return _create_for_users(
        user_ids,
        kind=Notification.KIND_CATEGORY_NEW_POST,
        title=f"Новое в «{category_label}»",
        body=post.title,
        post=post,
        category=post.category,
    )


def _notify_user(user_id, *, kind, title, body, post=None, payload=None) -> int:
    if not user_id:
        return 0
    if _recent_duplicate(user_id, kind, post_id=getattr(post, "pk", None)):
        return 0
    Notification.objects.create(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        post=post,
        payload=payload or {},
    )
    _maybe_email_user(user_id, subject=title, body=body)
    return 1


def _maybe_email_user(user_id, *, subject: str, body: str) -> None:
    from django.conf import settings
    from django.core.mail import send_mail

    if not getattr(settings, "NOTIFY_SELLER_EMAIL", True):
        return
    from accounts.models import User

    email = (
        User.objects.filter(pk=user_id)
        .exclude(email="")
        .values_list("email", flat=True)
        .first()
    )
    if not email:
        return
    try:
        send_mail(
            subject=f"{settings.SITE_NAME}: {subject}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        pass


def notify_seller_moderation(
    post,
    *,
    approved: bool,
    was_revision: bool = False,
    hidden: bool = False,
    reason: str = "",
) -> int:
    reason = (reason or "").strip()
    if approved:
        title = "Объявление опубликовано" if not was_revision else "Правки одобрены"
        body = (
            f"«{post.title}» теперь видно в поиске."
            if not was_revision
            else f"Правки к «{post.title}» опубликованы."
        )
        kind = Notification.KIND_MODERATION_APPROVED
    else:
        if was_revision:
            title = "Правки отклонены"
            body = f"Правки к «{post.title}» не приняты. На сайте осталась прежняя версия."
        elif hidden:
            title = "Объявление скрыто"
            body = f"«{post.title}» снято модерацией."
        else:
            title = "Объявление отклонено"
            body = f"«{post.title}» не прошло модерацию."
        if reason:
            body = f"{body} Причина: {reason}"[:500]
        kind = Notification.KIND_MODERATION_REJECTED
    return _notify_user(
        post.user_id,
        kind=kind,
        title=title,
        body=body,
        post=post,
        payload={"reason": reason} if reason else {},
    )


def notify_seller_expired(post) -> int:
    return _notify_user(
        post.user_id,
        kind=Notification.KIND_POST_EXPIRED,
        title="Срок объявления истёк",
        body=f"«{post.title}» снято с публикации. Можете отправить его на модерацию снова.",
        post=post,
    )


def notify_new_review(*, seller_id, reviewer_name: str, rating: int, post=None, review_id, is_update=False) -> int:
    if not seller_id:
        return 0
    stars = f"{rating}/5"
    if is_update:
        title = "Отзыв обновлён"
        body = f"{reviewer_name} изменил отзыв: {stars}."
    else:
        title = "Новый отзыв"
        body = f"{reviewer_name} оценил вас на {stars}."
    payload = {"seller_id": seller_id, "review_id": str(review_id)}
    # Avoid collapsing different reviews that share the same post within 1 minute.
    since = timezone.now() - timedelta(minutes=1)
    if Notification.objects.filter(
        user_id=seller_id,
        kind=Notification.KIND_NEW_REVIEW,
        created_at__gte=since,
        payload__review_id=str(review_id),
    ).exists():
        return 0
    Notification.objects.create(
        user_id=seller_id,
        kind=Notification.KIND_NEW_REVIEW,
        title=title,
        body=body[:500],
        post=post,
        payload=payload,
    )
    _maybe_email_user(seller_id, subject=title, body=body)
    return 1


def notify_review_reply(*, reviewer_id, seller_name: str, post=None, review_id, seller_id) -> int:
    if not reviewer_id:
        return 0
    title = "Ответ на отзыв"
    body = f"{seller_name} ответил на ваш отзыв."
    payload = {"seller_id": seller_id, "review_id": str(review_id)}
    since = timezone.now() - timedelta(minutes=1)
    if Notification.objects.filter(
        user_id=reviewer_id,
        kind=Notification.KIND_REVIEW_REPLY,
        created_at__gte=since,
        payload__review_id=str(review_id),
    ).exists():
        return 0
    Notification.objects.create(
        user_id=reviewer_id,
        kind=Notification.KIND_REVIEW_REPLY,
        title=title,
        body=body,
        post=post,
        payload=payload,
    )
    _maybe_email_user(reviewer_id, subject=title, body=body)
    return 1
