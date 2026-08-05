"""Paid listing boost via T-Bank payment form."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from listings.models import Post, Promotion
from listings.services.ranking import calculate_rank_score
from listings.services.tbank import TBankError, get_payment_state, init_payment, is_configured

PAID_STATUSES = frozenset({"CONFIRMED", "AUTHORIZED"})
FAILED_STATUSES = frozenset(
    {"REJECTED", "CANCELED", "DEADLINE_EXPIRED", "AUTH_FAIL", "REVERSED", "REFUNDED"}
)


class PromoteError(Exception):
    pass


def promote_price_rub() -> int:
    return int(getattr(settings, "PROMOTE_PRICE_RUB", 199))


def promote_days() -> int:
    return int(getattr(settings, "PROMOTE_DAYS", 7))


def promote_boost() -> float:
    return float(getattr(settings, "PROMOTE_BOOST", 2.0))


def promote_price_kopecks() -> int:
    return promote_price_rub() * 100


def promote_label() -> str:
    return f"{promote_price_rub()} ₽ / {promote_days()} дн."


@transaction.atomic
def start_promotion(post: Post, *, user, absolute_uri) -> str:
    """Create pending Promotion, call T-Bank Init, return PaymentURL."""
    if not is_configured():
        raise PromoteError("Оплата временно недоступна. Попробуйте позже.")
    if post.user_id != getattr(user, "id", None):
        raise PromoteError("Можно поднимать только свои объявления.")
    if post.status != "published":
        raise PromoteError("Поднять можно только опубликованное объявление.")

    amount = promote_price_kopecks()
    promo = Promotion.objects.create(
        post=post,
        type="boost",
        amount=amount,
        status="pending",
    )
    order_id = f"promo-{promo.pk}"
    notify_url = absolute_uri(reverse("tbank_notify"))
    success_url = absolute_uri(reverse("listings:promote_success", args=[post.pk]))
    fail_url = absolute_uri(reverse("listings:promote_fail", args=[post.pk]))

    item_name = f"Поднятие объявления на {promote_days()} дн."
    try:
        data = init_payment(
            amount_kopecks=amount,
            order_id=order_id,
            description=f"Поднятие объявления «{post.title[:80]}» на {promote_days()} дн.",
            notification_url=notify_url,
            success_url=success_url,
            fail_url=fail_url,
            customer_email=getattr(user, "email", None) or None,
            customer_phone=getattr(user, "phone", None) or None,
            item_name=item_name,
        )
    except TBankError as exc:
        promo.status = "failed"
        promo.save(update_fields=["status"])
        # Provider diagnostics are retained in the application log by the
        # gateway client, but must not be exposed in a browser message.
        raise PromoteError("Не удалось перейти к оплате. Попробуйте ещё раз позже.") from exc

    payment_id = str(data.get("PaymentId") or "")
    promo.payment_ref = payment_id
    promo.save(update_fields=["payment_ref"])
    return str(data["PaymentURL"])


@transaction.atomic
def apply_paid_promotion(promo: Promotion) -> Promotion:
    # Bank notifications can be retried concurrently. Lock the payment row, not
    # just the listing, so one payment can only grant one promotion period.
    # Keep the same post → promotion locking order as deferred activation.
    post = Post.objects.select_for_update().select_related("user").get(pk=promo.post_id)
    promo = Promotion.objects.select_for_update().get(pk=promo.pk)
    if promo.status in {"paid", "paid_pending_activation"}:
        return promo

    now = timezone.now()
    if post.status != "published" or post.expires_at <= now:
        promo.status = "paid_pending_activation"
        promo.save(update_fields=["status"])
        return promo

    return _activate_paid_promotion(promo, post, now=now)


def _activate_paid_promotion(promo: Promotion, post: Post, *, now) -> Promotion:
    """Apply a paid promotion to a locked, currently published listing."""
    days = promote_days()
    base = post.paid_until if post.paid_until and post.paid_until > now else now
    paid_until = base + timedelta(days=days)
    boost = promote_boost()

    post.paid_until = paid_until
    post.paid_boost = boost
    post.bumped_at = now
    post.rank_score = calculate_rank_score(post)
    post.updated_at = now
    post.save(
        update_fields=[
            "paid_until",
            "paid_boost",
            "bumped_at",
            "rank_score",
            "updated_at",
        ]
    )

    promo.status = "paid"
    promo.starts_at = now
    promo.ends_at = paid_until
    promo.save(update_fields=["status", "starts_at", "ends_at"])
    from bookmarks.services import notify_promotion_result

    transaction.on_commit(lambda: notify_promotion_result(promo, paid=True))
    return promo


@transaction.atomic
def activate_pending_promotions(post: Post) -> int:
    """Start paid boosts that arrived while the listing was not public."""
    post = Post.objects.select_for_update().get(pk=post.pk)
    now = timezone.now()
    if post.status != "published" or post.expires_at <= now:
        return 0
    promos = list(
        Promotion.objects.select_for_update()
        .filter(post=post, status="paid_pending_activation")
        .order_by("created_at", "pk")
    )
    for promo in promos:
        _activate_paid_promotion(promo, post, now=now)
    return len(promos)


def mark_promotion_failed(promo: Promotion) -> None:
    if promo.status in {"paid", "failed"}:
        return
    promo.status = "failed"
    promo.save(update_fields=["status"])
    from bookmarks.services import notify_promotion_result

    notify_promotion_result(promo, paid=False)


def find_promotion_for_notification(*, order_id: str, payment_id: str) -> Promotion | None:
    promo = None
    if order_id.startswith("promo-"):
        try:
            pk = int(order_id.removeprefix("promo-"))
            promo = Promotion.objects.select_related("post").filter(pk=pk).first()
        except ValueError:
            promo = None
    if promo is None and payment_id:
        promo = (
            Promotion.objects.select_related("post")
            .filter(payment_ref=str(payment_id))
            .first()
        )
    return promo


def latest_pending_promotion(post: Post) -> Promotion | None:
    return (
        Promotion.objects.filter(post=post, status="pending", type="boost")
        .order_by("-created_at")
        .first()
    )


def has_pending_promotion(post: Post) -> bool:
    return latest_pending_promotion(post) is not None


def sync_promotion_after_return(post: Post) -> str:
    """
    After bank SuccessURL: apply boost if already paid/confirmed.

    Returns one of: "promoted", "pending", "failed".
    """
    post.refresh_from_db()
    if post.is_promoted and not latest_pending_promotion(post):
        return "promoted"

    promo = latest_pending_promotion(post)
    if promo is None:
        return "promoted" if post.is_promoted else "failed"

    if not promo.payment_ref:
        return "pending"

    try:
        state = get_payment_state(promo.payment_ref)
    except TBankError:
        return "pending"

    status = str(state.get("Status") or "")
    if status in PAID_STATUSES:
        apply_paid_promotion(promo)
        post.refresh_from_db()
        return "promoted" if post.is_promoted else "pending"
    if status in FAILED_STATUSES:
        mark_promotion_failed(promo)
        return "failed"
    return "pending"
