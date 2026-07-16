from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count
from django.utils import timezone

from messaging.models import Conversation
from messaging.services import has_visible_messages_q
from reviews.models import PhoneReveal, SellerReview


class ReviewError(Exception):
    pass


def _phone_review_delay() -> timedelta:
    hours = max(0, int(getattr(settings, "REVIEW_AFTER_PHONE_HOURS", 2)))
    return timedelta(hours=hours)


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
    return _has_messaging_contact(reviewer, seller) or _has_phone_contact_ready(reviewer, seller)


def review_denied_message(reviewer, seller) -> str:
    unlock_at = phone_review_unlock_at(reviewer, seller)
    if unlock_at and timezone.now() < unlock_at:
        local = timezone.localtime(unlock_at)
        return (
            "Отзыв будет доступен после звонка — "
            f"примерно с {local.strftime('%d.%m %H:%M')}."
        )
    hours = int(getattr(settings, "REVIEW_AFTER_PHONE_HOURS", 2))
    if hours:
        return (
            "Отзыв можно оставить после переписки или после просмотра телефона "
            f"(через {hours} ч)."
        )
    return "Отзыв можно оставить после переписки или просмотра телефона продавца."


def eligible_conversation(reviewer, seller):
    return (
        Conversation.objects.filter(buyer=reviewer, seller=seller)
        .filter(has_visible_messages_q())
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
