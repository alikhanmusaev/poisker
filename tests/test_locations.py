from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from listings.models import Post
from listings.services.posts import ValidationError as PostValidationError
from listings.services.posts import create_post
from listings.services.search import search_posts
from locations.models import Region, Settlement


@pytest.fixture
def chechnya(db):
    region, _ = Region.objects.get_or_create(
        code="12",
        defaults={
            "name": "Чеченская Республика",
            "slug": "chechenskaya-respublika",
        },
    )
    if region.slug != "chechenskaya-respublika":
        region.slug = "chechenskaya-respublika"
        region.name = "Чеченская Республика"
        region.save(update_fields=["slug", "name"])
    grozny, _ = Settlement.objects.get_or_create(
        region=region,
        slug="grozny",
        defaults={"name": "Грозный", "type": "город", "population": 300000, "is_active": True},
    )
    return region, grozny


@pytest.mark.django_db
def test_location_search_requires_two_characters(client):
    response = client.get("/api/locations/search/", {"q": "г"})
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_location_search_returns_settlements(client, chechnya):
    _region, grozny = chechnya
    response = client.get("/api/locations/search/", {"q": "Гроз"})
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["results"]]
    assert grozny.id in ids
    row = next(r for r in response.json()["results"] if r["id"] == grozny.id)
    assert row["display_name"].startswith("Грозный")
    assert "region" in row


@pytest.mark.django_db
def test_search_filters_settlement_and_legacy_city(make_post, chechnya):
    region, grozny = chechnya
    argun = Settlement.objects.create(region=region, name="Аргун", slug="argun")
    now = timezone.now()
    matching = make_post(
        status="published", settlement=grozny, city="grozny", expires_at=now + timedelta(days=1)
    )
    legacy = make_post(
        status="published", settlement=None, city="grozny", expires_at=now + timedelta(days=1)
    )
    make_post(
        status="published", settlement=argun, city="argun", expires_at=now + timedelta(days=1)
    )

    results, total = search_posts("", settlement_id=grozny.id)
    assert total == 2
    assert {row["post"].id for row in results} == {matching.id, legacy.id}

    _results, region_total = search_posts("", region_id=region.id)
    assert region_total >= 1


@pytest.mark.django_db
def test_create_post_rejects_invalid_settlement_id(seller):
    with pytest.raises(PostValidationError):
        create_post(
            seller,
            {
                "title": "Продам телефон",
                "body": "Отличное состояние, полный комплект, без царапин.",
                "category": "elektronika",
                "settlement_id": 999999,
                "condition": "used",
                "price": 15000,
            },
        )


@pytest.mark.django_db
def test_create_post_with_settlement(chechnya, seller):
    _region, grozny = chechnya
    post = create_post(
        seller,
        {
            "title": "Продам телефон",
            "body": "Отличное состояние, полный комплект, без царапин.",
            "category": "elektronika",
            "settlement_id": grozny.id,
            "condition": "used",
            "price": 15000,
        },
    )
    assert post.settlement_id == grozny.id
    assert post.city == "grozny"
    assert Post.objects.filter(pk=post.pk).exists()


@pytest.mark.django_db
def test_region_and_settlement_urls(client, chechnya, make_post):
    region, grozny = chechnya
    now = timezone.now()
    make_post(
        status="published",
        settlement=grozny,
        city="grozny",
        expires_at=now + timedelta(days=1),
    )
    r = client.get(f"/{region.slug}/")
    assert r.status_code == 200
    s = client.get(f"/{region.slug}/{grozny.slug}/")
    assert s.status_code == 200
    legacy = client.get("/grozny/")
    assert legacy.status_code == 200


@pytest.mark.django_db
def test_empty_settlement_page_is_noindex(client, chechnya):
    region, grozny = chechnya
    response = client.get(f"/{region.slug}/{grozny.slug}/")
    assert response.status_code == 200
    assert b'name="robots" content="noindex,follow"' in response.content


@pytest.mark.django_db
def test_feed_select_related_no_n_plus_one(client, chechnya, make_post, django_assert_max_num_queries):
    region, grozny = chechnya
    now = timezone.now()
    for i in range(5):
        make_post(
            title=f"Товар {i}",
            status="published",
            settlement=grozny,
            city="grozny",
            expires_at=now + timedelta(days=1),
        )
    client.get(f"/{region.slug}/{grozny.slug}/")
    with django_assert_max_num_queries(40):
        response = client.get(f"/{region.slug}/{grozny.slug}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_import_locations_idempotent(tmp_path, chechnya, monkeypatch):
    region, _grozny = chechnya
    settlements = tmp_path / "settlements.csv"
    regions = tmp_path / "regions.csv"
    regions.write_text(
        "code,name,slug,geoname_id,federal_district\n"
        f"12,{region.name},{region.slug},2017370,\n",
        encoding="utf-8",
    )
    settlements.write_text(
        "region_code,region_name,name,type,slug,geoname_id,fias_id,latitude,longitude,population,timezone\n"
        f"12,{region.name},Гудермес,город,gudermes,999001,,43.3,46.1,50000,Europe/Moscow\n",
        encoding="utf-8",
    )
    call_command("import_locations", str(settlements), regions_csv=str(regions), skip_legacy_chechnya=True)
    call_command("import_locations", str(settlements), regions_csv=str(regions), skip_legacy_chechnya=True)
    assert Settlement.objects.filter(region=region, slug="gudermes").count() == 1


@pytest.mark.django_db
def test_backfill_post_settlements(make_post, chechnya):
    _region, grozny = chechnya
    post = make_post(settlement=None, city="grozny", status="draft")
    call_command("backfill_post_settlements")
    post.refresh_from_db()
    assert post.settlement_id == grozny.id
