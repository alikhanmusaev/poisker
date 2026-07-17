from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.services.seller_stats import annotate_seller_posts, seller_stats_summary
from bookmarks.models import PostBookmark
from messaging.models import Conversation, Message


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="stats-buyer@example.com",
        password="password12345",
        display_name="Stats Buyer",
        phone="+79005556677",
    )


@pytest.mark.django_db
def test_seller_stats_summary(seller, make_post, buyer):
    post = make_post(user=seller, status="published", title="Телефон stats")
    post.views = 100
    post.contact_clicks = 10
    post.expires_at = timezone.now() + timedelta(days=2)
    post.save(update_fields=["views", "contact_clicks", "expires_at"])

    PostBookmark.objects.create(user=buyer, post=post)
    conversation = Conversation.objects.create(post=post, buyer=buyer, seller=seller)
    Message.objects.create(conversation=conversation, sender=buyer, body="Здравствуйте")

    stats = seller_stats_summary(seller)
    assert stats["views_total"] == 100
    assert stats["contacts_total"] == 10
    assert stats["bookmarks_total"] == 1
    assert stats["conversations_total"] == 1
    assert stats["contact_rate"] == 10.0
    assert stats["expiring_soon"] == 1


@pytest.mark.django_db
def test_annotate_seller_posts(seller, make_post, buyer):
    post = make_post(user=seller, status="published", title="Annotated")
    PostBookmark.objects.create(user=buyer, post=post)
    Conversation.objects.create(post=post, buyer=buyer, seller=seller)
    annotated = annotate_seller_posts(post.__class__.objects.filter(pk=post.pk)).get()
    assert annotated.bookmarks_count == 1
    assert annotated.conversations_count == 1


@pytest.mark.django_db
def test_profile_shows_seller_stats(client, seller, make_post):
    post = make_post(user=seller, status="published", title="В профиле")
    post.views = 7
    post.contact_clicks = 2
    post.save(update_fields=["views", "contact_clicks"])
    client.force_login(seller)
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Статистика" in html
    assert "просмотров" in html
    assert ">7<" in html or "7</span>" in html
