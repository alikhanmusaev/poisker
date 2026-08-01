"""Geo cascade when local feed is empty."""

from datetime import timedelta

import pytest
from django.utils import timezone

from listings.services.geo_fallback import search_posts_with_geo_fallback
from locations.models import Region, Settlement


@pytest.fixture
def two_cities(db):
    region, _ = Region.objects.get_or_create(
        code="12",
        defaults={"name": "Чеченская Республика", "slug": "chechenskaya-respublika"},
    )
    other, _ = Region.objects.get_or_create(
        code="99",
        defaults={"name": "Другой регион", "slug": "drugoy-region"},
    )
    avtury, _ = Settlement.objects.get_or_create(
        region=region,
        slug="avtury",
        defaults={"name": "Автуры", "population": 10000, "is_active": True},
    )
    grozny, _ = Settlement.objects.get_or_create(
        region=region,
        slug="grozny",
        defaults={"name": "Грозный", "population": 300000, "is_active": True},
    )
    remote, _ = Settlement.objects.get_or_create(
        region=other,
        slug="remote-city",
        defaults={"name": "Дальний", "population": 50000, "is_active": True},
    )
    return region, other, avtury, grozny, remote


@pytest.mark.django_db
def test_fallback_to_region_when_settlement_empty(make_post, two_cities):
    region, _other, avtury, grozny, _remote = two_cities
    now = timezone.now()
    post = make_post(
        title="Телефон в Грозном",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=1),
    )
    found = search_posts_with_geo_fallback(
        query="",
        category="elektronika",
        settlement_id=avtury.id,
        settlement_name=avtury.name,
        region_name=region.name,
    )
    assert found.local_total == 0
    assert found.fallback == "region"
    assert found.total >= 1
    assert post.id in {row["post"].id for row in found.results}
    assert "Автуры" in found.fallback_label
    assert "Чеченская" in found.fallback_label


@pytest.mark.django_db
def test_fallback_to_all_when_region_empty(make_post, two_cities):
    region, _other, avtury, _grozny, remote = two_cities
    now = timezone.now()
    post = make_post(
        title="Товар далеко",
        status="published",
        settlement=remote,
        city="remote-city",
        category="elektronika",
        expires_at=now + timedelta(days=1),
    )
    found = search_posts_with_geo_fallback(
        query="",
        category="elektronika",
        settlement_id=avtury.id,
        settlement_name=avtury.name,
        region_name=region.name,
    )
    assert found.local_total == 0
    assert found.fallback == "all"
    assert found.total >= 1
    assert post.id in {row["post"].id for row in found.results}
    assert "России" in found.fallback_label


@pytest.mark.django_db
def test_no_fallback_when_local_has_results(make_post, two_cities):
    region, _other, avtury, grozny, _remote = two_cities
    now = timezone.now()
    local = make_post(
        title="Местный товар",
        status="published",
        settlement=avtury,
        city="avtury",
        category="elektronika",
        expires_at=now + timedelta(days=1),
    )
    make_post(
        title="Чужой товар",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=1),
    )
    found = search_posts_with_geo_fallback(
        query="",
        category="elektronika",
        settlement_id=avtury.id,
        settlement_name=avtury.name,
        region_name=region.name,
    )
    assert found.fallback is None
    assert found.local_total == 1
    assert found.total == 1
    assert found.results[0]["post"].id == local.id


@pytest.mark.django_db
def test_settlement_page_shows_region_fallback_banner(client, make_post, two_cities):
    region, _other, avtury, grozny, _remote = two_cities
    now = timezone.now()
    make_post(
        title="Смартфон Грозный",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=1),
    )
    response = client.get(f"/{region.slug}/{avtury.slug}/elektronika/")
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "feed-geo-fallback" in content
    assert "Автуры" in content
    assert "Смартфон Грозный" in content
