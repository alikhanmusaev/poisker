from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from bookmarks.models import Notification
from listings.services.posts import republish_post
from listings.services.search import _build_filter, _live_posts_qs
from listings.services.seo_urls import make_seo_slug
from moderation.services import approve_post, reject_post


@pytest.mark.django_db
def test_health_ok():
    client = Client()
    response = client.get(reverse("core:health"))
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.django_db
def test_ready_endpoint():
    client = Client()
    response = client.get(reverse("core:ready"))
    assert response.status_code in (200, 503)
    payload = response.json()
    assert "checks" in payload
    assert "database" in payload["checks"]


@pytest.mark.django_db
def test_robots_and_sitemap():
    client = Client()
    robots = client.get(reverse("core:robots"))
    assert robots.status_code == 200
    assert b"Sitemap:" in robots.content
    sitemap = client.get(reverse("core:sitemap"))
    assert sitemap.status_code == 200
    assert b"<urlset" in sitemap.content
    assert b"/nedvizhimost/" in sitemap.content


def test_make_seo_slug_transliterates_cyrillic():
    slug = make_seo_slug("Продам iPhone", "grozny")
    assert "prodam" in slug
    assert "iphone" in slug
    assert "obyavlenie" not in slug


@pytest.mark.django_db
def test_reject_requires_reason(staff_user, make_post):
    post = make_post()
    with pytest.raises(Exception):
        reject_post(post, staff_user, reason="   ")


@pytest.mark.django_db
def test_approve_sets_published_at_and_emails(staff_user, make_post, settings):
    settings.NOTIFY_SELLER_EMAIL = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    post = make_post(status="pending")
    approve_post(post, staff_user)
    post.refresh_from_db()
    assert post.status == "published"
    assert post.published_at is not None
    assert Notification.objects.filter(
        user=post.user, kind=Notification.KIND_MODERATION_APPROVED
    ).exists()
    assert mail.outbox


@pytest.mark.django_db
def test_reject_stores_note_and_notifies(staff_user, make_post, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    post = make_post(status="pending")
    reject_post(post, staff_user, reason="Неполное описание")
    post.refresh_from_db()
    assert post.status == "hidden"
    assert post.moderation_note == "Неполное описание"
    note = Notification.objects.filter(
        user=post.user, kind=Notification.KIND_MODERATION_REJECTED
    ).first()
    assert note
    assert "Неполное описание" in note.body
    assert mail.outbox


@pytest.mark.django_db
def test_rejected_unpublished_post_can_be_edited_and_resubmitted(seller, staff_user, make_post):
    post = make_post(status="pending", ever_published=False)
    reject_post(post, staff_user, reason="Исправьте описание")

    client = Client()
    assert client.login(email=seller.email, password="password12345")
    response = client.post(
        reverse("listings:edit", args=[post.pk]),
        {
            "title": "Обновлённый телефон",
            "body": "Подробное исправленное описание, достаточное для модерации.",
            "category": "elektronika",
            "city": post.city,
            "condition": "used",
            "price": "12000",
            "website": "",
        },
    )

    assert response.status_code == 302
    post.refresh_from_db()
    assert post.status == "pending"
    assert post.title == "Обновлённый телефон"
    assert post.moderation_note == ""


@pytest.mark.django_db
def test_hidden_published_post_still_cannot_be_edited(seller, make_post):
    post = make_post(status="hidden", ever_published=True)
    client = Client()
    assert client.login(email=seller.email, password="password12345")

    response = client.get(reverse("listings:edit", args=[post.pk]), follow=True)

    assert response.status_code == 200
    messages = [m.message for m in response.context["messages"]]
    assert any("Снятое объявление нельзя редактировать" in message for message in messages)


@pytest.mark.django_db
def test_republish_goes_to_pending(seller, make_post):
    post = make_post(status="hidden", expires_at=timezone.now() - timedelta(days=1))
    republish_post(post, seller)
    post.refresh_from_db()
    assert post.status == "pending"
    assert post.expires_at > timezone.now()


@pytest.mark.django_db
def test_live_posts_excludes_expired(make_post):
    live = make_post(status="published", expires_at=timezone.now() + timedelta(days=2))
    make_post(status="published", expires_at=timezone.now() - timedelta(hours=1), title="Старое")
    ids = set(_live_posts_qs().values_list("pk", flat=True))
    assert live.pk in ids
    assert len(ids) == 1


def test_typesense_filter_includes_expires():
    filt = _build_filter(None, None, None, None, False)
    assert "status:=published" in filt
    assert "expires_at:>=" in filt


@pytest.mark.django_db
def test_create_post_without_price_is_negotiable(seller, city_slug):
    client = Client()
    assert client.login(email=seller.email, password="password12345")
    response = client.post(
        reverse("listings:create"),
        {
            "title": "Товар без цены длинный",
            "body": "Описание достаточно длинное для публикации объявления без фиксированной цены.",
            "category": "elektronika",
            "city": city_slug,
            "condition": "used",
            "price": "",
            "website": "",
        },
    )
    assert response.status_code == 302
    from listings.models import Post

    post = Post.objects.get(title="Товар без цены длинный")
    assert post.price is None
    assert post.condition == "used"


@pytest.mark.django_db
def test_create_post_with_new_condition(seller, city_slug):
    client = Client()
    assert client.login(email=seller.email, password="password12345")
    response = client.post(
        reverse("listings:create"),
        {
            "title": "Новый товар длинный заголовок",
            "body": "Описание нового товара достаточно длинное для отправки на модерацию.",
            "category": "elektronika",
            "city": city_slug,
            "condition": "new",
            "price": "15000",
            "website": "",
        },
    )
    assert response.status_code == 302
    from listings.models import Post

    post = Post.objects.get(title="Новый товар длинный заголовок")
    assert post.price == 15000
    assert post.condition == "new"


@pytest.mark.django_db
def test_register_success(db):
    client = Client()
    response = client.post(
        reverse("accounts:register"),
        {
            "display_name": "Новый пользователь",
            "email": "newuser@example.com",
            "phone": "+79001112233",
            "password1": "UniquePass987!",
            "password2": "UniquePass987!",
            "accept_terms": "on",
            "accept_pdn": "on",
            "website": "",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith(reverse("accounts:register_done"))
    from accounts.models import User

    user = User.objects.get(email="newuser@example.com")
    assert user.email_verified is False
    assert user.pdn_consent_at is not None
    assert user.terms_accepted_at is not None
    assert client.session.get("_auth_user_id") is None


@pytest.mark.django_db
def test_register_requires_pdn_consent(db):
    client = Client()
    response = client.post(
        reverse("accounts:register"),
        {
            "display_name": "Без согласия",
            "email": "noconsent@example.com",
            "phone": "+79001112234",
            "password1": "UniquePass987!",
            "password2": "UniquePass987!",
            "accept_terms": "on",
            "website": "",
        },
    )
    assert response.status_code == 200
    from accounts.models import User

    assert not User.objects.filter(email="noconsent@example.com").exists()


@pytest.mark.django_db
def test_register_honeypot_blocks(db):
    client = Client()
    response = client.post(
        reverse("accounts:register"),
        {
            "display_name": "Bot",
            "email": "bot@example.com",
            "phone": "+79007778899",
            "password1": "password12345",
            "password2": "password12345",
            "website": "http://spam.example",
        },
    )
    assert response.status_code == 200
    from accounts.models import User

    assert not User.objects.filter(email="bot@example.com").exists()


@pytest.mark.django_db
def test_create_listing_honeypot_blocks(seller, city_slug):
    client = Client()
    assert client.login(email=seller.email, password="password12345")
    response = client.post(
        reverse("listings:create"),
        {
            "title": "Спам объявление длинное",
            "body": "Описание достаточно длинное для валидации формы объявления.",
            "category": "elektronika",
            "city": city_slug,
            "condition": "used",
            "price": "1000",
            "website": "http://spam.example",
        },
    )
    assert response.status_code == 200
    from listings.models import Post

    assert not Post.objects.filter(title="Спам объявление длинное").exists()


@pytest.mark.django_db
def test_notify_email_can_be_disabled(staff_user, make_post, settings):
    settings.NOTIFY_SELLER_EMAIL = False
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox.clear()
    post = make_post(status="pending")
    approve_post(post, staff_user)
    assert not mail.outbox
    assert Notification.objects.filter(
        user=post.user, kind=Notification.KIND_MODERATION_APPROVED
    ).exists()


@pytest.mark.django_db
def test_blocked_user_logged_out(seller):
    client = Client()
    assert client.login(email=seller.email, password="password12345")
    seller.is_blocked = True
    seller.save(update_fields=["is_blocked"])
    response = client.get(reverse("accounts:profile"))
    assert response.status_code in (302, 403)
