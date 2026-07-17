from datetime import timedelta

import os

# Ensure settings can load before Django initializes (pytest-django).
os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

import pytest
from django.utils import timezone

from accounts.models import User
from listings.constants import CITIES
from listings.models import Post


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    """Keep tests independent of Redis availability."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "poisker-tests",
        }
    }
    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]


@pytest.fixture
def city_slug():
    return next(iter(CITIES.keys()))


@pytest.fixture
def seller(db, city_slug):
    return User.objects.create_user(
        email="seller@example.com",
        password="password12345",
        display_name="Seller",
        phone="+79001112233",
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="mod@example.com",
        password="password12345",
        display_name="Mod",
        phone="+79004445566",
        is_staff=True,
    )


@pytest.fixture
def make_post(seller, city_slug):
    def _make(**kwargs):
        data = {
            "user": seller,
            "title": "Продам телефон",
            "body": "Хорошее состояние, полный комплект, торг уместен.",
            "category": "elektronika",
            "city": city_slug,
            "status": "pending",
            "contact_phone": seller.phone,
            "expires_at": timezone.now() + timedelta(days=30),
            "has_photo": False,
            "images": [],
        }
        data.update(kwargs)
        return Post.objects.create(**data)

    return _make
