"""Browse ranking: live freshness, softer photo bias, promo boost."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from listings.services.ranking import calculate_rank_score, completeness_score
from listings.services.search_ranking import compute_final_score


def test_completeness_photo_bonus_is_moderate():
    with_photo = SimpleNamespace(
        has_photo=True,
        images=["a.jpg"],
        price=None,
        body="",
        title="ab",
    )
    without = SimpleNamespace(
        has_photo=False,
        images=[],
        price=None,
        body="",
        title="ab",
    )
    assert completeness_score(with_photo) == 0.25
    assert completeness_score(without) == 0.0


def test_fresh_listing_without_photo_can_outrank_stale_with_photo():
    now = timezone.now()
    fresh = SimpleNamespace(
        city="grozny",
        rank_score=0.35,
        created_at=now,
        bumped_at=None,
        is_promoted=False,
        title="Смартфон без фото",
        price=10000,
        has_photo=False,
    )
    stale = SimpleNamespace(
        city="grozny",
        rank_score=0.55,
        created_at=now - timedelta(days=20),
        bumped_at=None,
        is_promoted=False,
        title="Смартфон с фото",
        price=10000,
        has_photo=True,
    )
    fresh_score = compute_final_score(
        fresh, 0, query="", mode="feed", max_text_match=1
    )
    stale_score = compute_final_score(
        stale, 0, query="", mode="feed", max_text_match=1
    )
    assert fresh_score > stale_score


def test_promoted_listing_outranks_similar_peer():
    now = timezone.now()
    base = dict(
        city="grozny",
        rank_score=0.5,
        created_at=now,
        bumped_at=None,
        title="Товар",
        price=5000,
    )
    promo = SimpleNamespace(**base, is_promoted=True)
    plain = SimpleNamespace(**base, is_promoted=False)
    assert compute_final_score(
        promo, 0, query="", mode="feed", max_text_match=1
    ) > compute_final_score(plain, 0, query="", mode="feed", max_text_match=1)


@pytest.mark.django_db
def test_stored_rank_score_excludes_freshness_decay(make_post):
    now = timezone.now()
    new = make_post(
        title="Новый товар полный",
        body="x" * 120,
        price=1000,
        has_photo=True,
        images=["/media/a.jpg"],
        status="published",
        created_at=now,
        expires_at=now + timedelta(days=30),
    )
    old = make_post(
        title="Старый товар полный",
        body="x" * 120,
        price=1000,
        has_photo=True,
        images=["/media/a.jpg"],
        status="published",
        created_at=now - timedelta(days=30),
        expires_at=now + timedelta(days=30),
    )
    # Same quality → stored scores should match (freshness is live-only now).
    assert calculate_rank_score(new) == calculate_rank_score(old)


@pytest.mark.django_db
def test_promotion_stats_only_count_current_promotion(make_post):
    from listings.models import Promotion
    from listings.ranking.promotion_service import PromotionService

    now = timezone.now()
    current_end = now + timedelta(days=7)
    post = make_post(status="published", paid_until=current_end)
    previous = Promotion.objects.create(
        post=post, type="boost", amount=19900, status="paid", ends_at=now + timedelta(days=3)
    )
    current = Promotion.objects.create(
        post=post, type="boost", amount=19900, status="paid", ends_at=current_end
    )

    PromotionService().record_impressions([post])
    PromotionService().record_click(post)
    previous.refresh_from_db()
    current.refresh_from_db()
    assert (previous.impressions, previous.clicks) == (0, 0)
    assert (current.impressions, current.clicks) == (1, 1)
