"""Short public listing URLs and legacy redirects."""

from app.services.seo import category_path, city_category_path


def test_seo_path_helpers():
    assert category_path("avto") == "/avto/"
    assert city_category_path("grozny") == "/grozny/"
    assert city_category_path("grozny", "avto") == "/grozny/avto/"


def test_new_category_url_returns_200(client):
    res = client.get("/avto/")
    assert res.status_code == 200
    assert "Авто" in res.get_data(as_text=True)


def test_new_city_url_returns_200(client):
    res = client.get("/grozny/")
    assert res.status_code == 200


def test_new_city_category_url_returns_200(client):
    res = client.get("/grozny/avto/")
    assert res.status_code == 200
    assert "Авто" in res.get_data(as_text=True)


def test_legacy_category_redirects(client):
    res = client.get("/kategoriya/avto", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers["Location"].endswith("/avto/")


def test_legacy_city_redirects(client):
    res = client.get("/gorod/grozny", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers["Location"].endswith("/grozny/")


def test_legacy_city_category_redirects(client):
    res = client.get("/gorod/grozny/avto", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers["Location"].endswith("/grozny/avto/")


def test_reserved_paths_not_hijacked(client):
    assert client.get("/privacy").status_code == 200
    assert client.get("/posts/new").status_code == 200
    assert client.get("/admin/login").status_code == 200


def test_index_category_query_redirects_to_short_url(client):
    res = client.get("/?category=avto", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers["Location"].endswith("/avto/")


def test_sitemap_uses_short_urls(client):
    text = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/kategoriya/" not in text
    assert "/gorod/" not in text
    assert "<loc>https://" in text or "<loc>http://" in text
    assert "/avto/" in text
    assert "/grozny/" in text
    assert "/grozny/avto/" in text


def test_category_page_canonical_is_short_url(client):
    res = client.get("/avto/")
    html = res.get_data(as_text=True)
    assert 'rel="canonical"' in html
    assert "/avto/" in html


def test_city_category_links_use_short_urls(client):
    res = client.get("/grozny/avto/")
    html = res.get_data(as_text=True)
    assert 'href="/grozny/avto/"' in html or 'href="/avto/"' in html
    assert "/kategoriya/" not in html.split("category-carousel")[1].split("</div>")[0]


def test_listing_pagination_preserves_short_path(client, app):
    from flask import render_template_string

    with app.test_request_context("/avto/"):
        html = render_template_string(
            '{% from "macros/listing.html" import listing_query_url with context %}{{ listing_query_url(2) }}',
            listing_path="/avto/",
            fixed_city=None,
            fixed_category="avto",
            query="",
            city="",
            category="avto",
            price_min=None,
            price_max=None,
            with_photo=False,
            with_price=False,
            sort="rank",
        )
    assert html.startswith("/avto/?")
    assert "page=2" in html
