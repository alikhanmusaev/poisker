from django.db import transaction
from django.utils import timezone

from listings.models import Post, Report
from listings.services.posts import ValidationError
from listings.services.ranking import calculate_rank_score
from listings.services.seo_urls import make_seo_slug

REASON_MAX_LEN = 400


def _require_staff(user):
    if not user.is_authenticated or not user.is_staff:
        raise ValidationError("Нет доступа.")


def _clean_reason(reason: str | None, *, required: bool = True) -> str:
    text = " ".join((reason or "").split())
    if required and not text:
        raise ValidationError("Укажите причину для продавца.")
    return text[:REASON_MAX_LEN]


def moderation_counts() -> dict:
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "pending": Post.objects.filter(status="pending").count(),
        "revisions": Post.objects.filter(status="published").exclude(pending_revision=None).count(),
        "reports_new": Report.objects.filter(status="new").count(),
        "hidden": Post.objects.filter(status="hidden").count(),
        "published_today": Post.objects.filter(
            status="published",
            published_at__gte=start,
        ).count(),
    }


def pending_queue():
    return (
        Post.objects.filter(status="pending")
        .select_related("user")
        .order_by("created_at")
    )


def revisions_queue():
    return (
        Post.objects.filter(status="published")
        .exclude(pending_revision=None)
        .select_related("user")
        .order_by("-updated_at", "-created_at")
    )


def hidden_queue():
    return (
        Post.objects.filter(status="hidden")
        .select_related("user")
        .order_by("-updated_at", "-created_at")
    )


def reports_queue(*, status: str = "new"):
    qs = Report.objects.select_related("post", "post__user", "reporter").order_by("-created_at")
    if status in ("new", "reviewed"):
        qs = qs.filter(status=status)
    return qs


@transaction.atomic
def approve_post(post: Post, user) -> Post:
    """Publish post and apply pending_revision fields if present."""
    _require_staff(user)
    if post.status == "deleted":
        raise ValidationError("Удалённое объявление нельзя опубликовать.")

    was_first_publish = post.status != "published"
    now = timezone.now()
    revision = post.pending_revision or {}
    if isinstance(revision, dict) and revision:
        if revision.get("title"):
            post.title = str(revision["title"]).strip()[:200]
        if revision.get("body") is not None:
            post.body = str(revision["body"]).strip()
        if revision.get("category"):
            post.category = str(revision["category"])
        if revision.get("city"):
            post.city = str(revision["city"])
        if "price" in revision:
            price = revision.get("price")
            post.price = None if price in ("", None) else price
        post.slug = make_seo_slug(post.title, post.city)

    post.pending_revision = None
    post.moderation_note = ""
    post.status = "published"
    post.ever_published = True
    post.published_at = now
    post.updated_at = now
    post.rank_score = calculate_rank_score(post)
    post.save()

    from bookmarks.services import notify_category_new_post, notify_seller_moderation

    if was_first_publish:
        notify_category_new_post(post)
    notify_seller_moderation(
        post,
        approved=True,
        was_revision=not was_first_publish,
    )
    from listings.services.search import index_post

    index_post(post)
    return post


@transaction.atomic
def reject_post(post: Post, user, *, reason: str = "") -> Post:
    """
    Reject pending listing (→ hidden) or discard a pending revision on a live listing.
    """
    _require_staff(user)
    if post.status == "deleted":
        raise ValidationError("Объявление уже удалено.")

    note = _clean_reason(reason, required=True)
    now = timezone.now()

    if post.status == "published" and post.pending_revision:
        post.pending_revision = None
        post.moderation_note = note
        post.updated_at = now
        post.save(update_fields=["pending_revision", "moderation_note", "updated_at"])
        from bookmarks.services import notify_seller_moderation

        notify_seller_moderation(post, approved=False, was_revision=True, reason=note)
        return post

    if post.status not in ("pending", "published", "hidden"):
        raise ValidationError("Это объявление нельзя отклонить.")

    was_published = post.status == "published"
    post.status = "hidden"
    post.pending_revision = None
    post.moderation_note = note
    post.updated_at = now
    post.save(update_fields=["status", "pending_revision", "moderation_note", "updated_at"])
    from bookmarks.services import notify_post_unpublished, notify_seller_moderation
    from listings.services.search import remove_post_from_index

    if was_published:
        notify_post_unpublished(post)
        remove_post_from_index(str(post.pk))
    notify_seller_moderation(post, approved=False, was_revision=False, reason=note)
    return post


@transaction.atomic
def hide_post(post: Post, user, *, reason: str = "") -> Post:
    _require_staff(user)
    if post.status != "published":
        raise ValidationError("Скрыть можно только опубликованное объявление.")
    note = _clean_reason(reason, required=True)
    now = timezone.now()
    post.status = "hidden"
    post.moderation_note = note
    post.updated_at = now
    post.save(update_fields=["status", "moderation_note", "updated_at"])
    from bookmarks.services import notify_post_unpublished, notify_seller_moderation
    from listings.services.search import remove_post_from_index

    notify_post_unpublished(post)
    notify_seller_moderation(post, approved=False, was_revision=False, hidden=True, reason=note)
    remove_post_from_index(str(post.pk))
    return post


@transaction.atomic
def mark_report_reviewed(report: Report, user) -> Report:
    _require_staff(user)
    if report.status == "reviewed":
        return report
    report.status = "reviewed"
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "reviewed_at"])
    return report


@transaction.atomic
def mark_post_reports_reviewed(post: Post, user) -> int:
    _require_staff(user)
    return Report.objects.filter(post=post, status="new").update(
        status="reviewed",
        reviewed_at=timezone.now(),
    )


@transaction.atomic
def resolve_reports_and_hide(post: Post, user, *, reason: str = "") -> Post:
    _require_staff(user)
    mark_post_reports_reviewed(post, user)
    if post.status == "published":
        return hide_post(post, user, reason=reason or "Скрыто по жалобам пользователей.")
    return post
