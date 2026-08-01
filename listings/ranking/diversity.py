"""Diversity constraints for feed construction."""

from __future__ import annotations

from listings.ranking.config import RankingSettings, get_ranking_settings


class DiversityService:
    def __init__(self, settings: RankingSettings | None = None):
        self.settings = settings or get_ranking_settings()

    def apply(self, items: list[dict], *, enforce_category: bool = True) -> list[dict]:
        if not self.settings.diversity_enabled or len(items) <= 1:
            return items

        remaining = list(items)
        output: list[dict] = []
        seen_ids: set = set()

        while remaining:
            pick_idx = None
            for idx, item in enumerate(remaining):
                post = item.get("post")
                if post is None:
                    pick_idx = idx
                    break
                if post.pk in seen_ids:
                    continue
                if self._violates(output, post, enforce_category=enforce_category):
                    continue
                pick_idx = idx
                break
            if pick_idx is None:
                # No diverse candidate — take best remaining unique.
                for idx, item in enumerate(remaining):
                    post = item.get("post")
                    if post is None or post.pk not in seen_ids:
                        pick_idx = idx
                        break
                if pick_idx is None:
                    break
            chosen = remaining.pop(pick_idx)
            post = chosen.get("post")
            if post is not None:
                seen_ids.add(post.pk)
            output.append(chosen)
        return output

    def _violates(self, output: list[dict], post, *, enforce_category: bool) -> bool:
        if not output:
            return False
        last = output[-1].get("post")
        if last is not None and last.user_id == post.user_id:
            return True

        # Max one seller in last screen window when configured to 1.
        window = max(1, self.settings.max_seller_per_screen)
        recent_sellers = {
            row["post"].user_id
            for row in output[-window:]
            if row.get("post") is not None
        }
        if post.user_id in recent_sellers and window <= 1:
            return True

        if enforce_category and self.settings.max_same_category_in_row > 0:
            streak = 0
            for row in reversed(output):
                p = row.get("post")
                if p is None or p.category != post.category:
                    break
                streak += 1
            if streak >= self.settings.max_same_category_in_row:
                return True

        if self.settings.max_promoted_in_row > 0 and post.is_promoted:
            streak = 0
            for row in reversed(output):
                p = row.get("post")
                if p is None or not p.is_promoted:
                    break
                streak += 1
            if streak >= self.settings.max_promoted_in_row:
                return True
        return False
