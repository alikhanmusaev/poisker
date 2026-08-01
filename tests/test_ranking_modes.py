"""Separated Home / Category / Search ranking."""

from datetime import timedelta

import pytest
from django.utils import timezone

from listings.ranking import RankingService
from listings.ranking.config import get_ranking_settings
from listings.ranking.diversity import DiversityService
from locations.models import Region, Settlement


@pytest.fixture
def cities(db):
    region, _ = Region.objects.get_or_create(
        code="12",
        defaults={"name": "Чеченская Республика", "slug": "chechenskaya-respublika"},
    )
    grozny, _ = Settlement.objects.get_or_create(
        region=region,
        slug="grozny",
        defaults={"name": "Грозный", "population": 300000, "is_active": True},
    )
    return region, grozny


@pytest.mark.django_db
def test_home_keeps_promoted_in_separate_block(make_post, cities, seller):
    region, grozny = cities
    now = timezone.now()
    organic = make_post(
        title="Обычный товар",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=10),
        paid_until=None,
    )
    promoted = make_post(
        title="Поднятый товар",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=10),
        paid_until=now + timedelta(days=3),
        paid_boost=1.0,
        bumped_at=now,
    )
    result = RankingService().build(
        settlement=grozny,
        mode="home",
        limit=20,
        page=1,
    )
    promo_ids = {row["post"].id for row in result.promoted}
    organic_ids = {row["post"].id for row in result.results}
    section_ids = {
        row["post"].id
        for key in ("new", "popular", "recommended")
        for row in result.sections.get(key, [])
    }
    assert promoted.id in promo_ids
    assert promoted.id not in organic_ids
    assert promoted.id not in section_ids
    assert organic.id not in promo_ids


@pytest.mark.django_db
def test_category_promoted_block_and_organic(make_post, cities):
    _region, grozny = cities
    now = timezone.now()
    make_post(
        title="Org A",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=10),
    )
    promoted = make_post(
        title="Promo A",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=10),
        paid_until=now + timedelta(days=2),
    )
    result = RankingService().build(
        category="elektronika",
        settlement=grozny,
        mode="category",
        page=1,
    )
    assert any(row["post"].id == promoted.id for row in result.promoted)
    assert all(row["post"].id != promoted.id for row in result.results)


@pytest.mark.django_db
def test_search_has_no_promoted_shelf(make_post, cities):
    _region, grozny = cities
    now = timezone.now()
    make_post(
        title="iPhone 13 Pro",
        body="Смартфон Apple",
        status="published",
        settlement=grozny,
        city="grozny",
        category="elektronika",
        expires_at=now + timedelta(days=10),
        paid_until=now + timedelta(days=2),
    )
    result = RankingService().build(
        query="iphone",
        settlement=grozny,
        mode="search",
        page=1,
    )
    assert result.promoted == []
    assert result.mode == "search"


def test_category_promotion_weight_capped():
    cfg = get_ranking_settings()
    assert cfg.category.promotion <= 0.10


def test_diversity_blocks_same_seller_streak():
    from types import SimpleNamespace

    items = [
        {"post": SimpleNamespace(pk=1, user_id=1, category="a", is_promoted=False)},
        {"post": SimpleNamespace(pk=2, user_id=1, category="b", is_promoted=False)},
        {"post": SimpleNamespace(pk=3, user_id=2, category="a", is_promoted=False)},
    ]
    out = DiversityService().apply(items, enforce_category=False)
    sellers = [i["post"].user_id for i in out]
    assert sellers[0] != sellers[1] or len(set(sellers)) == 1
