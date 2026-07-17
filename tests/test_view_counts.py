import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.utils import timezone

from listings.models import Post
from listings.services.show_context import increment_views


@pytest.mark.django_db
def test_views_counted_once_per_session():
    User = get_user_model()
    seller = User.objects.create_user(email="seller-views@example.com", password="x")
    post = Post.objects.create(
        user=seller,
        title="Тест просмотров",
        body="Описание",
        category="elektronika",
        city="grozny",
        status="published",
        expires_at=timezone.now() + timezone.timedelta(days=30),
        views=0,
    )
    factory = RequestFactory()
    request = factory.get("/")
    # Attach a real session via Client middleware-style
    client = Client()
    session = client.session
    request.session = session
    request.user = type("Anon", (), {"is_authenticated": False, "id": None})()

    assert increment_views(request, post) is True
    post.refresh_from_db()
    assert post.views == 1

    # Same session — no second count
    request.session = client.session
    assert increment_views(request, post) is False
    post.refresh_from_db()
    assert post.views == 1


@pytest.mark.django_db
def test_owner_views_not_counted():
    User = get_user_model()
    seller = User.objects.create_user(email="owner-views@example.com", password="x")
    post = Post.objects.create(
        user=seller,
        title="Тест владельца",
        body="Описание",
        category="elektronika",
        city="grozny",
        status="published",
        expires_at=timezone.now() + timezone.timedelta(days=30),
        views=0,
    )
    factory = RequestFactory()
    request = factory.get("/")
    request.session = {}
    request.user = seller

    assert increment_views(request, post) is False
    post.refresh_from_db()
    assert post.views == 0
