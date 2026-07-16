from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from listings.services.ranking import calculate_rank_score, seller_reputation_score
from messaging.models import Conversation, Message
from reviews.models import PhoneReveal, SellerReview
from reviews.services import can_review_seller, record_phone_reveal, reply_to_review, upsert_review
from bookmarks.models import Notification


def test_upsert_review_notifies_seller(conversation_with_message, buyer, seller):
    upsert_review(reviewer=buyer, seller=seller, rating=5, comment="Отлично")
    note = Notification.objects.filter(user=seller, kind=Notification.KIND_NEW_REVIEW).first()
    assert note is not None
    assert "5/5" in note.body
    assert note.payload.get("seller_id") == seller.id


def test_seller_reply_notifies_reviewer(conversation_with_message, buyer, seller):
    review = upsert_review(reviewer=buyer, seller=seller, rating=4, comment="Норм")
    reply_to_review(seller=seller, review_id=review.id, text="Спасибо за отзыв!")
    review.refresh_from_db()
    assert review.reply_text == "Спасибо за отзыв!"
    assert review.replied_at is not None
    note = Notification.objects.filter(user=buyer, kind=Notification.KIND_REVIEW_REPLY).first()
    assert note is not None
    assert note.payload.get("review_id") == str(review.id)


def test_seller_cannot_reply_twice(conversation_with_message, buyer, seller):
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
    assert can_review_seller(buyer, seller) is True
    assert can_review_seller(seller, buyer) is False


def test_phone_reveal_unlocks_after_delay(published_post, buyer, seller, settings):
    settings.REVIEW_AFTER_PHONE_HOURS = 2
    assert can_review_seller(buyer, seller) is False
    record_phone_reveal(reviewer=buyer, post=published_post)
    assert can_review_seller(buyer, seller) is False
    PhoneReveal.objects.filter(reviewer=buyer, seller=seller).update(
        created_at=timezone.now() - timedelta(hours=3)
    )
    assert can_review_seller(buyer, seller) is True


def test_upsert_review_via_phone(published_post, buyer, seller, settings):
    settings.REVIEW_AFTER_PHONE_HOURS = 0
    record_phone_reveal(reviewer=buyer, post=published_post)
    upsert_review(reviewer=buyer, seller=seller, rating=4, comment="По телефону ок")
    seller.refresh_from_db()
    assert seller.rating_count == 1
    assert seller.rating_avg == 4.0
    review = SellerReview.objects.get(reviewer=buyer, seller=seller)
    assert review.post_id == published_post.id


def test_upsert_review_updates_aggregates_and_rank(conversation_with_message, buyer, seller, published_post):
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
    client.force_login(buyer)
    url = reverse("reviews:review_seller", args=[seller.id])
    response = client.get(url)
    assert response.status_code == 200
    response = client.post(url, {"rating": "5", "comment": "Супер"})
    assert response.status_code == 302
    seller.refresh_from_db()
    assert seller.rating_count == 1
    assert seller.rating_avg == 5.0
