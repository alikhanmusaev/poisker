import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from listings.models import Post

TEST_PASSWORD = "PoiskerTest1!"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password=TEST_PASSWORD,
        display_name="Buyer",
        phone="+79001112244",
        email_verified=True,
    )


@pytest.fixture
def auth_client(api_client, buyer):
    refresh = RefreshToken.for_user(buyer)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def seller_auth_client(api_client, seller):
    seller.email_verified = True
    seller.set_password(TEST_PASSWORD)
    seller.save(update_fields=["email_verified", "password"])
    refresh = RefreshToken.for_user(seller)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def published_post(make_post, seller):
    return make_post(
        status="published",
        published_at=timezone.now(),
        ever_published=True,
        contact_phone=seller.phone,
    )
