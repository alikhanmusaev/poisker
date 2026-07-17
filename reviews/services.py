from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

from messaging.models import Conversation
from messaging.services import has_visible_messages_q
from reviews.models import PhoneReveal, SellerReview


class ReviewError(Exception):
    pass


def _phone_review_delay() -> timedelta:
    hours = max(0, int(getattr(settings, "REVIEW_AFTER_PHONE_HOURS", 2)))
    return timedelta(hours=hours)


def deal_confirm_timeout() -> timedelta:
    days = max(1, int(getattr(settings, "DEAL_CONFIRM_TIMEOUT_DAYS", 3)))
    return timedelta(days=days)


def review_reminder_delay() -> timedelta:
    days = max(1, int(getattr(settings, "REVIEW_REMINDER_DAYS", 1)))
    return timedelta(days=days)


def record_phone_reveal(*, reviewer, post) -> PhoneReveal | None:
    if not reviewer.is_authenticated:
        return None
    seller = post.user
    if reviewer.id == seller.id or getattr(reviewer, "is_blocked", False):
        return None
    reveal, _created = PhoneReveal.objects.get_or_create(
        reviewer=reviewer,
        seller=seller,
        defaults={"post": post},
    )
    return reveal


def _has_messaging_contact(reviewer, seller) -> bool:
    return Conversation.objects.filter(
        buyer=reviewer,
        seller=seller,
    ).filter(has_visible_messages_q()).exists()


def conversation_review_unlock_at(conversation) -> datetime | None:
    """When the buyer may leave a review for this conversation."""
    if conversation.buyer_deal_confirmed_at is None:
        return None
    if conversation.seller_deal_confirmed_at is not None:
        return max(
            conversation.buyer_deal_confirmed_at,
            conversation.seller_deal_confirmed_at,
        )
    return conversation.buyer_deal_confirmed_at + deal_confirm_timeout()


def conversation_allows_buyer_review(conversation, *, now=None) -> bool:
    unlock_at = conversation_review_unlock_at(conversation)
    if unlock_at is None:
        return False
    return (now or timezone.now()) >= unlock_at


def conversation_review_via_timeout(conversation, *, now=None) -> bool:
    if conversation.seller_deal_confirmed_at is not None:
        return False
    unlock_at = conversation_review_unlock_at(conversation)
    if unlock_at is None:
        return False
    return (now or timezone.now()) >= unlock_at


def _review_eligible_conversations_qs(reviewer, seller):
    now = timezone.now()
    timeout_before = now - deal_confirm_timeout()
    return (
        Conversation.objects.filter(buyer=reviewer, seller=seller)
        .filter(has_visible_messages_q())
        .filter(buyer_deal_confirmed_at__isnull=False)
        .filter(
            Q(seller_deal_confirmed_at__isnull=False)
            | Q(buyer_deal_confirmed_at__lte=timeout_before)
        )
    )


def _has_deal_confirmed(reviewer, seller) -> bool:
    return _review_eligible_conversations_qs(reviewer, seller).exists()


def phone_review_unlock_at(reviewer, seller):
    if not reviewer.is_authenticated:
        return None
    reveal = PhoneReveal.objects.filter(reviewer=reviewer, seller=seller).first()
    if not reveal:
        return None
    return reveal.created_at + _phone_review_delay()


def _has_phone_contact_ready(reviewer, seller) -> bool:
    unlock_at = phone_review_unlock_at(reviewer, seller)
    if unlock_at is None:
        return False
    return timezone.now() >= unlock_at


def can_review_seller(reviewer, seller) -> bool:
    if not reviewer.is_authenticated or reviewer.id == seller.id:
        return False
    if getattr(seller, "is_blocked", False) or getattr(reviewer, "is_blocked", False):
        return False
    return _has_deal_confirmed(reviewer, seller)


def needs_deal_confirmation(reviewer, seller) -> bool:
    if not reviewer.is_authenticated or reviewer.id == seller.id:
        return False
    if _has_deal_confirmed(reviewer, seller):
        return False
    return _has_messaging_contact(reviewer, seller)


def review_denied_message(reviewer, seller) -> str:
    if not _has_messaging_contact(reviewer, seller):
        return (
            "Отзыв можно оставить после переписки, когда обе стороны "
            "подтвердят успешную сделку в чате."
        )
    if _has_deal_confirmed(reviewer, seller):
        return "Отзыв недоступен."
    conversation = (
        Conversation.objects.filter(buyer=reviewer, seller=seller)
        .filter(has_visible_messages_q())
        .order_by("-updated_at")
        .first()
    )
    days = int(getattr(settings, "DEAL_CONFIRM_TIMEOUT_DAYS", 3))
    if conversation and conversation.buyer_deal_confirmed_at is None:
        return (
            "Подтвердите успешную сделку в чате. Отзыв станет доступен, "
            "когда продавец тоже подтвердит, либо через "
            f"{days} дн. после вашего подтверждения."
        )
    unlock_at = conversation_review_unlock_at(conversation) if conversation else None
    if unlock_at:
        local = timezone.localtime(unlock_at)
        return (
            "Ждём подтверждения продавца. Если он не ответит, отзыв откроется "
            f"примерно с {local.strftime('%d.%m %H:%M')}."
        )
    return (
        "Ждём подтверждения сделки от продавца в чате. "
        f"Если продавец не подтвердит, отзыв откроется через {days} дн."
    )


def eligible_conversation(reviewer, seller):
    return (
        _review_eligible_conversations_qs(reviewer, seller)
        .select_related("post")
        .order_by("-updated_at")
        .first()
    )


def eligible_phone_post(reviewer, seller):
    reveal = (
        PhoneReveal.objects.filter(reviewer=reviewer, seller=seller)
        .select_related("post")
        .first()
    )
    return reveal.post if reveal else None


def get_review(reviewer, seller):
    if not reviewer.is_authenticated:
        return None
    return SellerReview.objects.filter(reviewer=reviewer, seller=seller).first()


def upsert_review(*, reviewer, seller, rating: int, comment: str = "") -> SellerReview:
    if not can_review_seller(reviewer, seller):
        raise ReviewError(review_denied_message(reviewer, seller))
    conversation = eligible_conversation(reviewer, seller)
    post = conversation.post if conversation else eligible_phone_post(reviewer, seller)
    review, created = SellerReview.objects.update_or_create(
        reviewer=reviewer,
        seller=seller,
        defaults={
            "rating": rating,
            "comment": (comment or "").strip()[:1000],
            "conversation": conversation,
            "post": post,
        },
    )
    refresh_seller_rating(seller)
    from bookmarks.services import notify_new_review

    notify_new_review(
        seller_id=seller.id,
        reviewer_name=reviewer.display_name or reviewer.email,
        rating=rating,
        post=post,
        review_id=review.id,
        is_update=not created,
    )
    return review


def reply_to_review(*, seller, review_id, text: str) -> SellerReview:
    review = SellerReview.objects.select_related("reviewer", "post", "seller").filter(pk=review_id).first()
    if not review or review.seller_id != seller.id:
        raise ReviewError("Отзыв не найден.")
    if review.replied_at or (review.reply_text or "").strip():
        raise ReviewError("На этот отзыв уже есть ответ.")
    text = (text or "").strip()[:1000]
    if not text:
        raise ReviewError("Введите текст ответа.")
    review.reply_text = text
    review.replied_at = timezone.now()
    review.save(update_fields=["reply_text", "replied_at", "updated_at"])

    from bookmarks.services import notify_review_reply

    notify_review_reply(
        reviewer_id=review.reviewer_id,
        seller_name=seller.display_name or seller.email,
        post=review.post,
        review_id=review.id,
        seller_id=seller.id,
    )
    return review


def refresh_seller_rating(seller) -> None:
    agg = SellerReview.objects.filter(seller=seller).aggregate(
        avg=Avg("rating"),
        cnt=Count("id"),
    )
    seller.rating_avg = round(float(agg["avg"] or 0), 2)
    seller.rating_count = int(agg["cnt"] or 0)
    seller.save(update_fields=["rating_avg", "rating_count"])

    from django.db.models.signals import post_save

    from listings.models import Post
    from listings.services.ranking import calculate_rank_score
    from listings.services.search import upsert_posts_to_index
    from listings.signals import sync_search_index

    posts = list(
        Post.objects.filter(user=seller, status="published").select_related("user")
    )
    if not posts:
        return
    for post in posts:
        post.user = seller
        post.rank_score = calculate_rank_score(post)
    post_save.disconnect(sync_search_index, sender=Post)
    try:
        Post.objects.bulk_update(posts, ["rank_score"], batch_size=100)
    finally:
        post_save.connect(sync_search_index, sender=Post)
    upsert_posts_to_index(posts)


def seller_reviews_qs(seller):
    return (
        SellerReview.objects.filter(seller=seller)
        .select_related("reviewer", "post")
        .order_by("-created_at")
    )


def handle_deal_confirmation_side_effects(conversation, confirmer) -> None:
    """Notify the other party / unlock review after a deal confirmation click."""
    from bookmarks.services import notify_deal_confirm_request, notify_review_unlocked

    conversation.refresh_from_db()
    other = conversation.other_participant(confirmer)
    other_name = confirmer.display_name or confirmer.email
    post = conversation.post

    if conversation.both_deal_confirmed:
        notify_review_unlocked(
            buyer_id=conversation.buyer_id,
            post=post,
            conversation_id=conversation.id,
            seller_id=conversation.seller_id,
            via_timeout=False,
        )
        return

    notify_deal_confirm_request(
        user_id=other.id,
        post=post,
        conversation_id=conversation.id,
        other_name=other_name,
    )


def process_deal_review_jobs() -> dict:
    """Unlock-timeout notifications and review reminders (scheduler)."""
    from bookmarks.models import Notification
    from bookmarks.services import notify_review_reminder, notify_review_unlocked

    now = timezone.now()
    timeout_before = now - deal_confirm_timeout()
    reminder_before = now - review_reminder_delay()
    unlocked = 0
    reminded = 0

    timeout_candidates = (
        Conversation.objects.filter(
            buyer_deal_confirmed_at__isnull=False,
            buyer_deal_confirmed_at__lte=timeout_before,
            seller_deal_confirmed_at__isnull=True,
        )
        .filter(has_visible_messages_q())
        .select_related("post")
    )
    for conversation in timeout_candidates.iterator(chunk_size=100):
        if SellerReview.objects.filter(
            reviewer_id=conversation.buyer_id,
            seller_id=conversation.seller_id,
        ).exists():
            continue
        unlocked += notify_review_unlocked(
            buyer_id=conversation.buyer_id,
            post=conversation.post,
            conversation_id=conversation.id,
            seller_id=conversation.seller_id,
            via_timeout=True,
        )

    both_confirmed = (
        Conversation.objects.filter(
            buyer_deal_confirmed_at__isnull=False,
            seller_deal_confirmed_at__isnull=False,
        )
        .filter(has_visible_messages_q())
        .select_related("post")
    )
    timeout_unlocked = (
        Conversation.objects.filter(
            buyer_deal_confirmed_at__isnull=False,
            buyer_deal_confirmed_at__lte=timeout_before,
            seller_deal_confirmed_at__isnull=True,
        )
        .filter(has_visible_messages_q())
        .select_related("post")
    )

    seen = set()
    for conversation in list(both_confirmed[:500]) + list(timeout_unlocked[:500]):
        if conversation.pk in seen:
            continue
        seen.add(conversation.pk)
        unlock_at = conversation_review_unlock_at(conversation)
        if unlock_at is None or unlock_at > now:
            continue
        if SellerReview.objects.filter(
            reviewer_id=conversation.buyer_id,
            seller_id=conversation.seller_id,
        ).exists():
            continue
        unlock_note = Notification.objects.filter(
            user_id=conversation.buyer_id,
            kind=Notification.KIND_REVIEW_UNLOCKED,
            payload__conversation_id=str(conversation.id),
        ).first()
        if not unlock_note:
            notify_review_unlocked(
                buyer_id=conversation.buyer_id,
                post=conversation.post,
                conversation_id=conversation.id,
                seller_id=conversation.seller_id,
                via_timeout=conversation.seller_deal_confirmed_at is None,
            )
            continue
        if unlock_note.created_at > reminder_before:
            continue
        reminded += notify_review_reminder(
            buyer_id=conversation.buyer_id,
            post=conversation.post,
            conversation_id=conversation.id,
            seller_id=conversation.seller_id,
        )

    return {"unlocked": unlocked, "reminded": reminded}
