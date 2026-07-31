"""Paid listing boost via T-Bank payment form."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from listings.models import Post, Promotion
from listings.services.ranking import calculate_rank_score
from listings.services.tbank import TBankError, init_payment, is_configured


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

    try:
        data = init_payment(
            amount_kopecks=amount,
            order_id=order_id,
            description=f"Поднятие объявления «{post.title[:80]}» на {promote_days()} дн.",
            notification_url=notify_url,
            success_url=success_url,
            fail_url=fail_url,
            customer_email=getattr(user, "email", None) or None,
        )
    except TBankError as exc:
        promo.status = "failed"
        promo.save(update_fields=["status"])
        raise PromoteError(str(exc) or "Не удалось создать платёж.") from exc

    payment_id = str(data.get("PaymentId") or "")
    promo.payment_ref = payment_id
    promo.save(update_fields=["payment_ref"])
    return str(data["PaymentURL"])


@transaction.atomic
def apply_paid_promotion(promo: Promotion) -> Promotion:
    if promo.status == "paid":
        return promo

    post = Post.objects.select_for_update().select_related("user").get(pk=promo.post_id)
    now = timezone.now()
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
    return promo


def mark_promotion_failed(promo: Promotion) -> None:
    if promo.status == "paid":
        return
    promo.status = "failed"
    promo.save(update_fields=["status"])


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
