"""Fair rotation for promoted listings."""

from __future__ import annotations

import random
from datetime import timedelta

from django.utils import timezone

from listings.models import Post, Promotion
from listings.ranking.config import RankingSettings, get_ranking_settings


class RotationService:
    def __init__(self, settings: RankingSettings | None = None):
        self.settings = settings or get_ranking_settings()

    def rotate(self, posts: list[Post]) -> list[Post]:
        if not posts:
            return []
        if not self.settings.promotion_rotation_enabled or len(posts) == 1:
            return list(posts)

        now = timezone.now()
        promo_map = self._latest_paid_promos(posts)

        def key(post: Post):
            promo = promo_map.get(post.pk)
            impressions = int(getattr(promo, "impressions", 0) or 0)
            clicks = int(getattr(promo, "clicks", 0) or 0)
            last = getattr(promo, "last_shown_at", None)
            # Prefer fewer impressions, then older last show, then fewer clicks.
            age_hours = 9999.0
            if last is not None:
                age_hours = max((now - last).total_seconds() / 3600.0, 0.0)
            return (impressions, -age_hours, clicks, random.random())

        return sorted(posts, key=key)

    def _latest_paid_promos(self, posts: list[Post]) -> dict:
        ids = [p.pk for p in posts]
        rows = (
            Promotion.objects.filter(post_id__in=ids, status="paid")
            .order_by("post_id", "-starts_at", "-id")
        )
        out = {}
        for promo in rows:
            if promo.post_id not in out:
                out[promo.post_id] = promo
        return out
