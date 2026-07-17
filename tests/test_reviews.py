from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from listings.services.ranking import calculate_rank_score, seller_reputation_score
from messaging.models import Conversation, Message
from messaging.services import confirm_deal_completed
from reviews.models import PhoneReveal, SellerReview
from reviews.services import (
    ReviewError,
    can_review_seller,
    process_deal_review_jobs,
    record_phone_reveal,
    reply_to_review,
    upsert_review,
)
from bookmarks.models import Notification


def confirm_deal_both_sides(conversation):
    now = timezone.now()
    conversation.buyer_deal_confirmed_at = now
    conversation.seller_deal_confirmed_at = now
    conversation.save(update_fields=["buyer_deal_confirmed_at", "seller_deal_confirmed_at"])


def test_upsert_review_notifies_seller(conversation_with_message, buyer, seller):
    confirm_deal_both_sides(conversation_with_message)
    upsert_review(reviewer=buyer, seller=seller, rating=5, comment="Отлично")
    note = Notification.objects.filter(user=seller, kind=Notification.KIND_NEW_REVIEW).first()
    assert note is not None
    assert "5/5" in note.body
    assert note.payload.get("seller_id") == seller.id


def test_seller_reply_notifies_reviewer(conversation_with_message, buyer, seller):
    confirm_deal_both_sides(conversation_with_message)
    review = upsert_review(reviewer=buyer, seller=seller, rating=4, comment="Норм")
    reply_to_review(seller=seller, review_id=review.id, text="Спасибо за отзыв!")
    review.refresh_from_db()
    assert review.reply_text == "Спасибо за отзыв!"
    assert review.replied_at is not None
    note = Notification.objects.filter(user=buyer, kind=Notification.KIND_REVIEW_REPLY).first()
    assert note is not None
    assert note.payload.get("review_id") == str(review.id)


def test_seller_cannot_reply_twice(conversation_with_message, buyer, seller):
    confirm_deal_both_sides(conversation_with_message)
    review = upsert_review(reviewer=buyer, seller=seller, rating=5, comment="Топ")
    reply_to_review(seller=seller, review_id=review.id, text="Спасибо")
    with pytest.raises(Exception):
        reply_to_review(seller=seller, review_id=review.id, text="Ещё раз")


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="password12345",
        display_name="Buyer",
        phone="+79009998877",
    )


@pytest.fixture
def published_post(make_post):
    post = make_post(status="published", title="Телефон Samsung")
    post.rank_score = calculate_rank_score(post)
    post.save(update_fields=["rank_score"])
    return post


@pytest.fixture
def conversation_with_message(published_post, buyer, seller):
    conversation = Conversation.objects.create(
        post=published_post,
        buyer=buyer,
        seller=seller,
    )
    Message.objects.create(
        conversation=conversation,
        sender=buyer,
        body="Здравствуйте, товар ещё актуален?",
    )
    return conversation


def test_cannot_review_without_contact(buyer, seller):
    assert can_review_seller(buyer, seller) is False


def test_can_review_after_messaging(conversation_with_message, buyer, seller):
    assert can_review_seller(buyer, seller) is False
    confirm_deal_both_sides(conversation_with_message)
    assert can_review_seller(buyer, seller) is True
    assert can_review_seller(seller, buyer) is False


def test_phone_reveal_does_not_unlock_review_without_deal(published_post, buyer, seller, settings):
    settings.REVIEW_AFTER_PHONE_HOURS = 2
    assert can_review_seller(buyer, seller) is False
    record_phone_reveal(reviewer=buyer, post=published_post)
    PhoneReveal.objects.filter(reviewer=buyer, seller=seller).update(
        created_at=timezone.now() - timedelta(hours=3)
    )
    assert can_review_seller(buyer, seller) is False


def test_upsert_review_via_phone_requires_deal_confirmation(
    published_post, buyer, seller, conversation_with_message, settings
):
    settings.REVIEW_AFTER_PHONE_HOURS = 0
    record_phone_reveal(reviewer=buyer, post=published_post)
    with pytest.raises(ReviewError):
        upsert_review(reviewer=buyer, seller=seller, rating=4, comment="По телефону ок")
    confirm_deal_both_sides(conversation_with_message)
    upsert_review(reviewer=buyer, seller=seller, rating=4, comment="По телефону ок")
    seller.refresh_from_db()
    assert seller.rating_count == 1
    assert seller.rating_avg == 4.0
    review = SellerReview.objects.get(reviewer=buyer, seller=seller)
    assert review.post_id == published_post.id


def test_upsert_review_updates_aggregates_and_rank(conversation_with_message, buyer, seller, published_post):
    confirm_deal_both_sides(conversation_with_message)
    before = published_post.rank_score
    upsert_review(reviewer=buyer, seller=seller, rating=5, comment="Отличный продавец")
    seller.refresh_from_db()
    published_post.refresh_from_db()
    assert seller.rating_avg == 5.0
    assert seller.rating_count == 1
    assert SellerReview.objects.filter(seller=seller).count() == 1
    assert published_post.rank_score >= before


def test_seller_reputation_neutral_without_reviews():
    user = SimpleNamespace(rating_avg=0, rating_count=0)
    assert seller_reputation_score(user) == 0.5


def test_high_rating_beats_low_rating(seller, make_post):
    low = User.objects.create_user(
        email="low@example.com",
        password="password12345",
        display_name="Low",
        phone="+79001110001",
        rating_avg=2.0,
        rating_count=10,
    )
    high = User.objects.create_user(
        email="high@example.com",
        password="password12345",
        display_name="High",
        phone="+79001110002",
        rating_avg=5.0,
        rating_count=10,
    )
    now = timezone.now()
    low_post = make_post(user=low, status="published", title="A", created_at=now)
    high_post = make_post(user=high, status="published", title="B", created_at=now)
    # Override auto timestamps if needed — create_at may be auto_now_add
    Post = low_post.__class__
    Post.objects.filter(pk=low_post.pk).update(created_at=now)
    Post.objects.filter(pk=high_post.pk).update(created_at=now)
    low_post.refresh_from_db()
    high_post.refresh_from_db()
    low_post.user = low
    high_post.user = high
    assert calculate_rank_score(high_post) > calculate_rank_score(low_post)


def test_confirm_deal_idempotent(conversation_with_message, buyer, seller):
    confirm_deal_completed(conversation_with_message, buyer)
    confirm_deal_completed(conversation_with_message, buyer)
    conversation_with_message.refresh_from_db()
    assert conversation_with_message.buyer_deal_confirmed_at is not None
    assert conversation_with_message.seller_deal_confirmed_at is None


@pytest.mark.django_db
def test_confirm_deal_view(client, conversation_with_message, buyer):
    client.force_login(buyer)
    url = reverse("messaging:confirm_deal", args=[conversation_with_message.id])
    response = client.post(url)
    assert response.status_code == 302
    conversation_with_message.refresh_from_db()
    assert conversation_with_message.buyer_deal_confirmed_at is not None


@pytest.mark.django_db
def test_review_requires_both_deal_confirmations(client, conversation_with_message, buyer, seller):
    client.force_login(buyer)
    url = reverse("reviews:review_seller", args=[seller.id])
    assert client.get(url).status_code == 302

    confirm_deal_completed(conversation_with_message, buyer)
    assert client.get(url).status_code == 302

    confirm_deal_completed(conversation_with_message, seller)
    assert client.get(url).status_code == 200
    response = client.post(url, {"rating": "5", "comment": "Супер"})
    assert response.status_code == 302
    seller.refresh_from_db()
    assert seller.rating_count == 1


@pytest.mark.django_db
def test_seller_profile_public(client, seller, published_post):
    url = reverse("reviews:seller_profile", args=[seller.id])
    response = client.get(url)
    assert response.status_code == 200
    assert seller.display_name.encode() in response.content


@pytest.mark.django_db
def test_review_form_requires_messaging(client, buyer, seller):
    client.force_login(buyer)
    url = reverse("reviews:review_seller", args=[seller.id])
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_review_form_ok_after_chat(client, conversation_with_message, buyer, seller):
    confirm_deal_both_sides(conversation_with_message)
    client.force_login(buyer)
    url = reverse("reviews:review_seller", args=[seller.id])
    response = client.get(url)
    assert response.status_code == 200
    response = client.post(url, {"rating": "5", "comment": "Супер"})
    assert response.status_code == 302
    seller.refresh_from_db()
    assert seller.rating_count == 1
    assert seller.rating_avg == 5.0


def test_buyer_can_review_after_timeout_without_seller(conversation_with_message, buyer, seller, settings):
    settings.DEAL_CONFIRM_TIMEOUT_DAYS = 3
    confirm_deal_completed(conversation_with_message, buyer)
    assert can_review_seller(buyer, seller) is False
    Conversation.objects.filter(pk=conversation_with_message.pk).update(
        buyer_deal_confirmed_at=timezone.now() - timedelta(days=3, hours=1)
    )
    assert can_review_seller(buyer, seller) is True


def test_confirm_notifies_other_party(conversation_with_message, buyer, seller):
    confirm_deal_completed(conversation_with_message, buyer)
    note = Notification.objects.filter(
        user=seller, kind=Notification.KIND_DEAL_CONFIRM_REQUEST
    ).first()
    assert note is not None
    assert str(conversation_with_message.id) == note.payload.get("conversation_id")


def test_both_confirm_unlocks_review_notification(conversation_with_message, buyer, seller):
    confirm_deal_completed(conversation_with_message, buyer)
    confirm_deal_completed(conversation_with_message, seller)
    note = Notification.objects.filter(
        user=buyer, kind=Notification.KIND_REVIEW_UNLOCKED
    ).first()
    assert note is not None
    assert "отзыв" in note.body.lower() or "Отзыв" in note.title or "отзыв" in note.title.lower()


def test_process_deal_review_jobs_timeout_and_reminder(
    conversation_with_message, buyer, seller, settings
):
    settings.DEAL_CONFIRM_TIMEOUT_DAYS = 3
    settings.REVIEW_REMINDER_DAYS = 1
    confirm_deal_completed(conversation_with_message, buyer)
    Conversation.objects.filter(pk=conversation_with_message.pk).update(
        buyer_deal_confirmed_at=timezone.now() - timedelta(days=4)
    )
    result = process_deal_review_jobs()
    assert result["unlocked"] >= 1
    unlock = Notification.objects.filter(
        user=buyer, kind=Notification.KIND_REVIEW_UNLOCKED
    ).first()
    assert unlock is not None

    # Make unlock old enough for reminder
    Notification.objects.filter(pk=unlock.pk).update(
        created_at=timezone.now() - timedelta(days=2)
    )
    Conversation.objects.filter(pk=conversation_with_message.pk).update(
        buyer_deal_confirmed_at=timezone.now() - timedelta(days=5)
    )
    result = process_deal_review_jobs()
    assert result["reminded"] >= 1
    assert Notification.objects.filter(
        user=buyer, kind=Notification.KIND_REVIEW_REMINDER
    ).exists()
