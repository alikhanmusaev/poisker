"""Promotion inventory, stats, and paid product hooks."""

from __future__ import annotations

from django.db.models import F
from django.utils import timezone

from listings.models import Post, Promotion
from listings.ranking.rotation import RotationService


# Future paid products map to bonus kinds without changing ranking formulas.
BONUS_KINDS = {
    "boost": {"organic_weight_key": "promotion", "block": "promoted"},
    "vip": {"organic_weight_key": "promotion", "block": "promoted", "badge": "vip"},
    "premium": {"organic_weight_key": "promotion", "block": "promoted", "badge": "premium"},
    "pin": {"organic_weight_key": "promotion", "block": "pinned"},
    "urgent": {"organic_weight_key": "promotion", "block": "promoted", "badge": "urgent"},
    "highlight": {"card_style": "highlight"},
    "frame": {"card_style": "frame"},
    "autobump": {"action": "bump"},
    "guaranteed_shows": {"block": "promoted", "fair_rotation": True},
}


class PromotionService:
    """Active boosts, rotation, and impression/click accounting."""

    def __init__(self, rotation: RotationService | None = None):
        self.rotation = rotation or RotationService()

    def active_promoted_qs(self, *, category: str | None = None, settlement_id=None, region_id=None):
        now = timezone.now()
        qs = (
            Post.objects.filter(
                status="published",
                expires_at__gte=now,
                paid_until__gt=now,
            )
            .select_related("user", "settlement", "settlement__region")
        )
        if category:
            qs = qs.filter(category=category)
        if settlement_id:
            qs = qs.filter(settlement_id=settlement_id)
        elif region_id:
            qs = qs.filter(settlement__region_id=region_id)
        return qs

    def promoted_for_block(
        self,
        *,
        limit: int,
        category: str | None = None,
        settlement_id=None,
        region_id=None,
        exclude_ids: set | None = None,
    ) -> list[Post]:
        qs = self.active_promoted_qs(
            category=category, settlement_id=settlement_id, region_id=region_id
        )
        if exclude_ids:
            qs = qs.exclude(pk__in=exclude_ids)
        posts = list(qs[: max(limit * 4, limit)])
        rotated = self.rotation.rotate(posts)
        # Seller diversity inside promo block: prefer unique sellers.
        picked: list[Post] = []
        seen_sellers: set = set()
        for post in rotated:
            if post.user_id in seen_sellers:
                continue
            picked.append(post)
            seen_sellers.add(post.user_id)
            if len(picked) >= limit:
                break
        if len(picked) < limit:
            for post in rotated:
                if post in picked:
                    continue
                picked.append(post)
                if len(picked) >= limit:
                    break
        self.record_impressions(picked)
        return picked

    def record_impressions(self, posts: list[Post]) -> None:
        if not posts:
            return
        now = timezone.now()
        for post in posts:
            Promotion.objects.filter(
                post=post,
                status="paid",
                ends_at=post.paid_until,
                ends_at__gt=now,
            ).update(
                impressions=F("impressions") + 1,
                last_shown_at=now,
            )
        )

    def record_click(self, post: Post) -> None:
        now = timezone.now()
        Promotion.objects.filter(
            post=post,
            status="paid",
            ends_at=post.paid_until,
            ends_at__gt=now,
        ).update(clicks=F("clicks") + 1)

    def bonus_kinds(self) -> dict:
        return BONUS_KINDS
