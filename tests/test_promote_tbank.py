"""Tests for T-Bank paid listing boost."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from listings.models import Post, Promotion
from listings.services.promote import apply_paid_promotion, promote_price_kopecks
from listings.services.tbank import generate_token, verify_notification


@pytest.mark.django_db
def test_generate_token_stable():
    payload = {
        "TerminalKey": "DemoTerminal",
        "Amount": 19900,
        "OrderId": "promo-1",
        "Description": "test",
    }
    token = generate_token(payload, password="secret")
    assert len(token) == 64
    assert token == generate_token(payload, password="secret")
    assert token != generate_token(payload, password="other")


@pytest.mark.django_db
def test_verify_notification_roundtrip(settings):
    settings.TBANK_PASSWORD = "secret"
    settings.TBANK_TERMINAL_KEY = "DemoTerminal"
    payload = {
        "TerminalKey": "DemoTerminal",
        "OrderId": "promo-1",
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 12345,
        "Amount": 19900,
    }
    payload["Token"] = generate_token(payload, password="secret")
    assert verify_notification(payload) is True
    payload["Token"] = "deadbeef"
    assert verify_notification(payload) is False


@pytest.mark.django_db
def test_apply_paid_promotion_sets_boost(seller, make_post, settings):
    settings.PROMOTE_DAYS = 7
    settings.PROMOTE_BOOST = 2.0
    post = make_post(user=seller, status="published")
    promo = Promotion.objects.create(
        post=post, type="boost", amount=19900, status="pending", payment_ref="1"
    )
    apply_paid_promotion(promo)
    post.refresh_from_db()
    promo.refresh_from_db()
    assert promo.status == "paid"
    assert post.is_promoted
    assert post.paid_boost == 2.0
    assert post.bumped_at is not None
    assert post.paid_until > timezone.now() + timedelta(days=6)


@pytest.mark.django_db
def test_promote_requires_owner(seller, make_post, client, settings):
    settings.TBANK_TERMINAL_KEY = "Demo"
    settings.TBANK_PASSWORD = "pass"
    post = make_post(user=seller, status="published")
    other = Client()
    from accounts.models import User

    stranger = User.objects.create_user(
        email="stranger@example.com",
        password="password12345",
        display_name="Stranger",
        phone="+79001112234",
    )
    other.force_login(stranger)
    response = other.post(reverse("listings:promote", args=[post.pk]))
    assert response.status_code in (302, 404)
    assert Promotion.objects.count() == 0


@pytest.mark.django_db
def test_promote_starts_payment(seller, make_post, client, settings):
    settings.TBANK_TERMINAL_KEY = "Demo"
    settings.TBANK_PASSWORD = "pass"
    settings.PROMOTE_PRICE_RUB = 199
    post = make_post(user=seller, status="published")
    client.force_login(seller)
    fake = {
        "Success": True,
        "PaymentId": 999001,
        "PaymentURL": "https://securepay.tinkoff.ru/html/payForm/pay?id=999001",
        "Status": "NEW",
    }
    with patch("listings.services.promote.init_payment", return_value=fake) as mocked:
        response = client.post(reverse("listings:promote", args=[post.pk]))
    assert response.status_code == 302
    assert response["Location"] == fake["PaymentURL"]
    mocked.assert_called_once()
    promo = Promotion.objects.get()
    assert promo.status == "pending"
    assert promo.payment_ref == "999001"
    assert promo.amount == promote_price_kopecks()


@pytest.mark.django_db
def test_tbank_notify_confirms(seller, make_post, client, settings):
    settings.TBANK_TERMINAL_KEY = "Demo"
    settings.TBANK_PASSWORD = "secret"
    settings.PROMOTE_DAYS = 7
    settings.PROMOTE_BOOST = 2.5
    post = make_post(user=seller, status="published")
    promo = Promotion.objects.create(
        post=post, type="boost", amount=19900, status="pending", payment_ref="555"
    )
    payload = {
        "TerminalKey": "Demo",
        "OrderId": f"promo-{promo.pk}",
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 555,
        "Amount": 19900,
    }
    payload["Token"] = generate_token(payload, password="secret")
    response = client.post(
        reverse("tbank_notify"),
        data=payload,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.content == b"OK"
    post.refresh_from_db()
    promo.refresh_from_db()
    assert promo.status == "paid"
    assert post.is_promoted
    assert post.paid_boost == 2.5
