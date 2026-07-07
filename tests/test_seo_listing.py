"""Listing URL helpers and SEO listing UX."""

from app.services.seo import listing_page_url, listing_should_noindex


def test_listing_page_url_preserves_category_path():
    url = listing_page_url(
        "/avto/",
        page=2,
        category="avto",
        fixed_category="avto",
        sort="rank",
    )
    assert url.startswith("/avto/?")
    assert "page=2" in url
    assert "sort=rank" in url
    assert "category=" not in url


def test_listing_page_url_preserves_city_and_category_path():
    url = listing_page_url(
        "/grozny/avto/",
        page=3,
        city="grozny",
        category="avto",
        fixed_city="grozny",
        fixed_category="avto",
        price_min=1000,
    )
    assert url.startswith("/grozny/avto/?")
    assert "page=3" in url
    assert "price_min=1000" in url
    assert "city=" not in url
    assert "category=" not in url


def test_listing_page_url_home_with_filters():
    url = listing_page_url(
        "/",
        page=2,
        query="iphone",
        category="elektronika",
        price_max=50000,
        with_photo=True,
        sort="relevance",
    )
    assert "q=iphone" in url
    assert "category=elektronika" in url
    assert "price_max=50000" in url
    assert "with_photo=1" in url
    assert "sort=relevance" in url
    assert "page=2" in url
    assert url.startswith("/?")


def test_listing_should_noindex_clean_category_page():
    assert not listing_should_noindex(page=1, sort="rank")


def test_listing_should_noindex_search_and_filters():
    assert listing_should_noindex(page=1, query="iphone")
    assert listing_should_noindex(page=1, price_min=1000)
    assert listing_should_noindex(page=1, with_photo=True)
    assert listing_should_noindex(page=1, sort="price_asc")
    assert listing_should_noindex(page=2)


def test_listing_search_page_has_noindex(client):
    res = client.get("/?q=iphone")
    assert res.status_code == 200
    assert 'content="noindex, follow"' in res.get_data(as_text=True)


def test_listing_category_page_is_indexable(client):
    res = client.get("/avto/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'content="index, follow"' in html
    assert 'content="noindex, follow"' not in html


def test_listing_sorted_category_page_has_noindex(client):
    res = client.get("/avto/?sort=price_asc")
    assert res.status_code == 200
    assert 'content="noindex, follow"' in res.get_data(as_text=True)


def test_homepage_has_website_json_ld(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert '"@type": "WebSite"' in html or '"@type":"WebSite"' in html
    assert "SearchAction" in html


def test_indexable_listing_has_og_image(client):
    res = client.get("/avto/")
    assert res.status_code == 200
    assert 'property="og:image"' in res.get_data(as_text=True)


def test_post_image_alt_helper():
    from app.services.seo import post_image_alt

    assert post_image_alt("Холодильник", 2, 3) == "Холодильник — фото 2 из 3"
    assert post_image_alt("  Диван  ") == "Диван — фото"


def test_post_title_max_len_is_50():
    from app.constants import POST_TITLE_MAX_LEN

    assert POST_TITLE_MAX_LEN == 50


def test_support_email_default(app):
    with app.app_context():
        assert app.config["SUPPORT_EMAIL"] == "info@poisker.ru"


def test_privacy_page_shows_support_email(client):
    text = client.get("/privacy").get_data(as_text=True)
    assert "info@poisker.ru" in text


def test_listing_macro_outputs_path(app):
    from flask import render_template_string

    with app.test_request_context("/grozny/"):
        html = render_template_string(
            '{% from "macros/listing.html" import listing_query_url with context %}{{ listing_query_url(2) }}',
            listing_path="/grozny/",
            fixed_city="grozny",
            fixed_category=None,
            query="",
            city="grozny",
            category="",
            price_min=None,
            price_max=None,
            with_photo=False,
            with_price=False,
            sort="rank",
        )
    assert html.startswith("/grozny/?")
    assert "page=2" in html


def test_city_category_page_has_category_links(client):
    res = client.get("/grozny/avto/", follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'href="/grozny/avto/"' in html or 'href="/avto/"' in html
    assert 'class="category-chip' in html
    assert "<button" not in html.split("category-carousel")[1].split("</div>")[0]


def test_post_show_has_breadcrumbs(client, app):
    from tests.conftest import create_test_post

    with app.app_context():
        post = create_test_post(
            app,
            title="Тестовое объявление для крошек",
            city="grozny",
            category="avto",
        )
        slug = post.slug

    res = client.get(f"/obyavlenie/grozny/avto/{slug}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'class="breadcrumbs"' in html
    assert 'href="/grozny/"' in html
    assert 'href="/grozny/avto/"' in html
    assert "Тестовое объявление для крошек" in html
