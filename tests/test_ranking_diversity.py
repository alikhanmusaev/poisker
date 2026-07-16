from types import SimpleNamespace

import pytest

from listings.services.geo_preference import (
    PREFERRED_CITY_COOKIE,
    preferred_city_from_request,
    resolve_boost_city,
)
from listings.services.search_ranking import (
    compute_final_score,
    diversify_by_seller,
    geo_boost,
)


def test_geo_boost_matches_city():
    post = SimpleNamespace(city="grozny")
    assert geo_boost(post, "grozny") == 1.0
    assert geo_boost(post, "argun") == 0.0
    assert geo_boost(post, None) == 0.0


def test_geo_raises_feed_score():
    local = SimpleNamespace(
        city="grozny",
        rank_score=0.5,
        created_at=None,
        is_promoted=False,
        title="Телефон",
        price=1000,
    )
    # freshness_score needs created_at — use a real datetime
    from django.utils import timezone

    local.created_at = timezone.now()
    remote = SimpleNamespace(**{**local.__dict__, "city": "argun"})

    local_score = compute_final_score(
        local, 0, query="", mode="feed", max_text_match=1, boost_city="grozny"
    )
    remote_score = compute_final_score(
        remote, 0, query="", mode="feed", max_text_match=1, boost_city="grozny"
    )
    assert local_score > remote_score


def test_diversify_by_seller_breaks_streaks():
    def item(user_id, title):
        return {"post": SimpleNamespace(user_id=user_id, title=title), "score": 1}

    # Same seller dominates top scores
    ranked = [
        item(1, "a1"),
        item(1, "a2"),
        item(1, "a3"),
        item(2, "b1"),
        item(3, "c1"),
        item(2, "b2"),
    ]
    diversified = diversify_by_seller(ranked, min_gap=2)
    sellers = [row["post"].user_id for row in diversified]
    # First three should not all be seller 1
    assert sellers[:3] != [1, 1, 1]
    # No two identical sellers within gap of 2 when alternatives exist
    for i in range(len(sellers)):
        window = sellers[max(0, i - 2) : i]
        if sellers[i] in window:
            # Only allowed when no alternative was left — for this input
            # early positions must be diverse.
            assert i >= 4


def test_resolve_boost_city_skips_when_filtered():
    request = SimpleNamespace(COOKIES={PREFERRED_CITY_COOKIE: "grozny"})
    assert resolve_boost_city(request, filtered_city="grozny") is None
    assert resolve_boost_city(request, filtered_city=None) == "grozny"
    assert preferred_city_from_request(SimpleNamespace(COOKIES={})) is None


@pytest.mark.django_db
def test_home_redirects_to_preferred_city(client):
    client.cookies[PREFERRED_CITY_COOKIE] = "grozny"
    response = client.get("/")
    assert response.status_code == 302
    assert response.url.startswith("/grozny/")


@pytest.mark.django_db
def test_all_flag_clears_preferred_city(client):
    client.cookies[PREFERRED_CITY_COOKIE] = "grozny"
    response = client.get("/?all=1")
    assert response.status_code == 302
    assert response.url == "/"
    assert PREFERRED_CITY_COOKIE in response.cookies
    assert response.cookies[PREFERRED_CITY_COOKIE].value == ""
