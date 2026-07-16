from types import SimpleNamespace

from core.http import get_client_ip
from core.ratelimit import hit_rate_limit
from listings.services.ranking import recalculate_all_rank_scores


def test_get_client_ip_prefers_x_real_ip(settings):
    settings.TRUST_PROXY = True
    request = SimpleNamespace(
        META={
            "HTTP_X_FORWARDED_FOR": "1.2.3.4, 10.0.0.1",
            "HTTP_X_REAL_IP": "9.9.9.9",
            "REMOTE_ADDR": "127.0.0.1",
        }
    )
    assert get_client_ip(request) == "9.9.9.9"


def test_get_client_ip_ignores_spoofed_xff_without_real_ip(settings):
    settings.TRUST_PROXY = True
    request = SimpleNamespace(
        META={
            "HTTP_X_FORWARDED_FOR": "1.2.3.4, 10.0.0.1",
            "REMOTE_ADDR": "172.18.0.5",
        }
    )
    # Without X-Real-IP, fall back to REMOTE_ADDR (nginx → app), not client XFF.
    assert get_client_ip(request) == "172.18.0.5"


def test_rate_limit_blocks_after_limit(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "rate-test",
        }
    }
    key = "test-rate-limit-key"
    assert hit_rate_limit(key, limit=2, window_seconds=60) is False
    assert hit_rate_limit(key, limit=2, window_seconds=60) is False
    assert hit_rate_limit(key, limit=2, window_seconds=60) is True


def test_recalculate_ranks_bulk(db, make_post, seller):
    posts = [
        make_post(status="published", title=f"Item {i}", user=seller)
        for i in range(3)
    ]
    for post in posts:
        post.rank_score = 0
        post.save(update_fields=["rank_score"])
    n = recalculate_all_rank_scores()
    assert n == 3
    for post in posts:
        post.refresh_from_db()
        assert post.rank_score > 0
