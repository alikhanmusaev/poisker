"""Basic tests for Chechnya Board."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.posts import PostLimitError, ValidationError, create_post, update_post


def post_public_path(post) -> str:
    return f"/obyavlenie/{post.city}/{post.category}/{post.slug}"


def test_index(client):
    assert client.get("/").status_code == 200


def test_index_rejects_negative_page(client):
    assert client.get("/?page=-3").status_code == 200


def test_create_page_not_rate_limited(client):
    for _ in range(10):
        assert client.get("/posts/new").status_code == 200


def test_create_page_has_image_preview_controls(client):
    res = client.get("/posts/new")
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert len(text) > 8000, f"unexpected short response ({len(text)} bytes)"
    assert "post-wizard-form" in text
    assert 'class="image-picker"' in text
    assert 'class="sr-only image-picker-input"' in text
    assert 'data-total-max="5"' in text
    assert "Добавить фото" in text
    assert "Опубликовать" in text
    assert 'id="post-submit-preview"' in text
    assert 'create-wizard.js' in text
    assert 'publish-success.js' in text
    assert 'wizard-publish-success' in text
    assert 'publish-success' in text
    assert 'for="seller_name"' in text
    assert 'for="phone"' in text
    assert 'class="field-row"' in text


def test_create_post_ajax_json(client):
    res = client.post(
        "/posts/new",
        data={
            "title": "Тестовое объявление",
            "seller_name": "Ахмад",
            "body": "Подробное описание товара для теста публикации.",
            "category": "prodazha",
            "city": "grozny",
            "phone": "+79001234567",
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["post_id"]
    assert data["edit_url"].startswith("http")
    assert data["view_url"].startswith("http")
    assert data["title"] == "Тестовое объявление"


def test_success_page_uses_publish_panel(client, app):
    from app.services.posts import create_post

    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Объявление для success",
                "body": "Описание объявления для страницы успеха.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001112233",
            },
            ip_hash="test",
        )
        token = post.edit_token

    res = client.get(f"/posts/{post.id}/success?token={token}")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert 'class="publish-success"' in text
    assert "Сохраните ссылку" in text
    assert "publish-success.js" in text
    assert "Не закрывайте страницу" not in text


def test_my_posts_page(client):
    res = client.get("/posts/my")
    assert res.status_code == 200
    text = res.get_data(as_text=True)
    assert "my-posts-list" in text
    assert "my-posts.js" in text

    js = open(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "js", "my-posts.js"),
        encoding="utf-8",
    ).read()
    assert "Смотреть" in js


def test_image_url_helper(app):
    from app.routes.media import resolve_image_url

    with app.test_request_context():
        assert resolve_image_url("/media/posts/abc.jpg").endswith("/media/posts/abc.jpg")
        assert resolve_image_url("http://localhost:9000/board-images/posts/abc.jpg").endswith(
            "/media/posts/abc.jpg"
        )
        assert resolve_image_url("/static/demo/avto.jpg") == "/static/demo/avto.jpg"


def test_load_more_partial(client, app):
    from unittest.mock import patch

    with app.app_context():
        for i in range(21):
            create_post(
                {
                    "seller_name": "Ахмад",
                "title": f"Объявление {i}",
                    "body": "Тестовое описание для пагинации ленты.",
                    "category": "prodazha",
                    "city": "grozny",
                    "phone": f"+7900{i:07d}",
                    "price": 1000 + i,
                    "images": [],
                },
                ip_hash=f"test-{i}",
            )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        res = client.get("/", headers={"HX-Request": "true"})
        assert res.status_code == 200
        assert 'id="post-grid"' in res.get_data(as_text=True)

        res2 = client.get("/?page=2", headers={"HX-Request": "true"})
        assert res2.status_code == 200
        text = res2.get_data(as_text=True)
        assert "post-grid-append" in text
        assert 'id="post-grid"' not in text


def test_create_post_requires_seller_name(app):
    with app.app_context():
        with pytest.raises(ValidationError, match="имя"):
            create_post(
                {
                    "seller_name": " ",
                    "title": "Продам диван",
                    "body": "Диван в хорошем состоянии, самовывоз из Грозного.",
                    "category": "prodazha",
                    "city": "grozny",
                    "phone": "+79001112299",
                    "price": 5000,
                    "images": [],
                },
                ip_hash="no-name",
            )


def test_create_post_and_limit(app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продам диван",
                "body": "Диван в хорошем состоянии, самовывоз из Грозного.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001112233",
                "price": 5000,
                "images": [],
            },
            ip_hash="test",
        )
        assert post.id
        with pytest.raises(PostLimitError):
            create_post(
                {
                    "seller_name": "Ахмад",
                "title": "Ещё одно",
                    "body": "Второе объявление с того же номера за день.",
                    "category": "prodazha",
                    "city": "grozny",
                    "phone": "+79001112233",
                    "images": [],
                }
            )


def test_post_detail_has_back_link(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продам монитор",
                "body": "Монитор в хорошем состоянии, показывает ярко и без полос.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79004440000",
                "price": 9000,
                "images": [],
            },
            ip_hash="detail-back",
        )
        path = post_public_path(post)

    res = client.get(
        path,
        headers={"Referer": "http://localhost/?q=Грозный+монитор"},
    )

    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Назад к объявлениям" in text
    assert 'href="http://localhost/?q=Грозный+монитор"' in text


def test_index_has_sort_labels(client):
    res = client.get("/")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "По дешевле" in text
    assert "По дороже" in text


def test_index_with_price_filter(client, app):
    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "С ценой",
                "body": "Объявление с указанной ценой для фильтра.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110001",
                "price": 15000,
                "images": [],
            },
            ip_hash="priced",
        )
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Без цены",
                "body": "Объявление без цены для проверки фильтра с ценой.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110002",
                "price": None,
                "images": [],
            },
            ip_hash="unpriced",
        )

    res = client.get("/?with_price=1")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "С ценой" in text
    assert "Без цены" not in text


def test_post_meta_endpoint(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Мета тест",
                "body": "Проверка JSON-метаданных объявления для списка Мои.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110003",
                "price": 1000,
                "images": [],
            },
            ip_hash="meta",
        )
        post_id = post.id

    res = client.get(f"/posts/{post_id}/meta")
    data = res.get_json()
    assert res.status_code == 200
    assert data["ok"] is True
    assert data["title"] == "Мета тест"


def test_post_detail_has_og_tags(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "OG тест",
                "body": "Описание для Open Graph превью в мессенджерах.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110004",
                "price": 2000,
                "images": ["/static/demo/prodazha.jpg"],
            },
            ip_hash="og",
        )
        path = post_public_path(post)

    res = client.get(path)
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert 'property="og:title"' in text
    assert "OG тест" in text
    assert 'application/ld+json' in text
    assert 'rel="canonical"' in text


def test_post_detail_has_image_gallery(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продам телефон",
                "body": "Телефон в отличном состоянии, полный комплект и чеки.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79005556677",
                "price": 25000,
                "images": ["/static/demo/elektronika.jpg", "/static/demo/prodazha.jpg"],
            },
            ip_hash="gallery",
        )
        path = post_public_path(post)

    res = client.get(path)
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert 'data-post-gallery' in text
    assert 'post-gallery-track' in text
    assert 'post-lightbox' in text
    assert 'post-gallery.js' in text


def test_index_has_poisker_branding(client):
    res = client.get("/")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Поискер" in text
    assert 'rel="canonical"' in text


def test_robots_txt(client):
    res = client.get("/robots.txt")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Sitemap:" in text
    assert "/obyavlenie/" in text


def test_sitemap_xml_lists_posts(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Sitemap тест",
                "body": "Проверка наличия объявления в карте сайта для SEO.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110005",
                "price": 3000,
                "images": [],
            },
            ip_hash="sitemap",
        )
        path = post_public_path(post)

    res = client.get("/sitemap.xml")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert path in text


def test_legacy_slug_url_redirects_to_canonical(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Старый slug URL",
                "body": "Проверка редиректа с короткого URL объявления.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110007",
                "price": 5000,
                "images": [],
            },
            ip_hash="legacy-slug",
        )
        path = post_public_path(post)
        slug = post.slug

    res = client.get(f"/obyavlenie/{slug}", follow_redirects=False)
    assert res.status_code == 301
    assert path in res.location


def test_wrong_city_category_redirects(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Неверный путь",
                "body": "Проверка редиректа при неверном городе или категории в URL.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110008",
                "price": 6000,
                "images": [],
            },
            ip_hash="wrong-path",
        )
        path = post_public_path(post)
        slug = post.slug

    res = client.get(f"/obyavlenie/grozny/prodazha/{slug}", follow_redirects=False)
    assert res.status_code == 301
    assert path in res.location


def test_legacy_post_url_redirects_to_slug(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Редирект тест",
                "body": "Проверка постоянного редиректа со старого URL на slug.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110006",
                "price": 4000,
                "images": [],
            },
            ip_hash="redirect",
        )
        post_id = post.id
        path = post_public_path(post)

    res = client.get(f"/posts/{post_id}", follow_redirects=False)
    assert res.status_code == 301
    assert path in res.location


def test_meta_can_edit_with_valid_token(client, app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Проверка редактирования",
                "body": "Проверка флага can_edit в meta для владельца объявления.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79001110009",
                "price": 7000,
                "images": [],
            },
            ip_hash="can-edit",
        )
        post_id = post.id
        token = post.edit_token

    res = client.get(f"/posts/{post_id}/meta?token={token}")
    data = res.get_json()
    assert res.status_code == 200
    assert data["can_edit"] is True

    res_bad = client.get(f"/posts/{post_id}/meta?token=wrong-token")
    data_bad = res_bad.get_json()
    assert data_bad["can_edit"] is False


def test_create_page_has_phone_mask(client):
    res = client.get("/posts/new")
    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "phone-mask.js" in text
    assert 'type="tel"' in text


def test_update_post_rejects_negative_price(app):
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продам стол",
                "body": "Крепкий деревянный стол в хорошем состоянии.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79005550000",
                "price": 1000,
                "images": [],
            },
            ip_hash="test-update",
        )
        with pytest.raises(ValidationError):
            update_post(
                post,
                {
                    "seller_name": "Ахмад",
                "title": post.title,
                    "body": post.body,
                    "category": post.category,
                    "price": -1,
                    "images": post.images,
                },
            )


def test_search_on_home(client):
    assert client.get("/?q=диван").status_code == 200
    assert client.get("/search?q=диван").status_code == 302


def test_search_falls_back_when_index_is_empty(app):
    from unittest.mock import patch

    from app.services.search import search_posts

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продам велосипед",
                "body": "Горный велосипед в хорошем состоянии, недавно обслужен.",
                "category": "sport",
                "city": "grozny",
                "phone": "+79007770000",
                "price": 12000,
                "images": [],
            },
            ip_hash="test-empty-index",
        )

        with patch(
            "app.services.search._typesense_search",
            return_value={"hits": [], "found": 0},
        ):
            results, total = search_posts(query="", city=None, category=None)

        assert total == 1
        assert results[0]["post"].title == "Продам велосипед"


def test_search_ignores_stale_index_total(app):
    from unittest.mock import patch

    from app.services.search import search_posts

    with app.app_context():
        with patch(
            "app.services.search._typesense_search",
            return_value={
                "hits": [{"document": {"id": "missing-post-id"}, "highlights": []}],
                "found": 13,
            },
        ):
            results, total = search_posts(query="телефон", city="grozny", price_max=60000)

    assert results == []
    assert total == 0


def test_price_and_photo_filters(client, app):
    from unittest.mock import patch

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Телефон с фото",
                "body": "Хороший телефон с комплектом и фотографиями.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79007770001",
                "price": 15000,
                "images": ["/static/demo/elektronika.jpg"],
            },
            ip_hash="filter-a",
        )
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Телефон без фото",
                "body": "Рабочий телефон без фотографии в объявлении.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79007770002",
                "price": 5000,
                "images": [],
            },
            ip_hash="filter-b",
        )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        res = client.get("/?price_min=10000&with_photo=1")

    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Телефон с фото" in text
    assert "Телефон без фото" not in text


def test_smart_query_extracts_city_and_price():
    from app.services.smart_query import parse_search_query

    parsed = parse_search_query("Грозный айфон до 50000 с фото")

    assert parsed["city"] == "grozny"
    assert parsed["price_max"] == 50000
    assert parsed["with_photo"] is True
    assert parsed["text"] == "айфон"
    assert parsed["category"] == "elektronika"
    assert "iphone" in parsed["expanded_terms"]


def test_home_smart_query_filters_results(client, app):
    from unittest.mock import patch

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "айфон в Грозном",
                "body": "Телефон в хорошем состоянии, полный комплект.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79007770003",
                "price": 45000,
                "images": [],
            },
            ip_hash="smart-a",
        )
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "айфон в Шали",
                "body": "Телефон в хорошем состоянии, полный комплект.",
                "category": "elektronika",
                "city": "shali",
                "phone": "+79007770004",
                "price": 45000,
                "images": [],
            },
            ip_hash="smart-b",
        )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        res = client.get("/?q=Грозный айфон до 50000")

    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "айфон в Грозном" in text
    assert "айфон в Шали" not in text


def test_legal_pages(client):
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200
    assert client.get("/guidelines").status_code == 200


def test_service_worker(client):
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.content_type


def test_assetlinks_empty_without_config(client):
    res = client.get("/.well-known/assetlinks.json")
    assert res.status_code == 200
    assert res.get_json() == []


def test_negative_price_filters_ignored(client, app):
    from unittest.mock import patch

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Дешёвый товар",
                "body": "Товар в хорошем состоянии, продаю недорого в Грозном.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79008880001",
                "price": 500,
                "images": [],
            },
            ip_hash="neg-price",
        )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        res = client.get("/?price_min=-100")

    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "Дешёвый товар" in text


def test_feed_sorts_by_rank_score(app):
    from unittest.mock import patch

    from app.services.search import search_posts

    with app.app_context():
        low = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Старое объявление",
                "body": "Описание старого объявления для проверки сортировки ленты.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79008880002",
                "price": 1000,
                "images": [],
            },
            ip_hash="rank-low",
        )
        high = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продвигаемое объявление",
                "body": "Описание продвигаемого объявления для проверки сортировки ленты.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79008880003",
                "price": 1000,
                "images": [],
            },
            ip_hash="rank-high",
        )
        high.rank_score = 10.0
        low.rank_score = 0.1
        from app.extensions import db

        db.session.commit()

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        with app.app_context():
            results, _ = search_posts(query="", sort="rank")

    assert results[0]["post"].title == "Продвигаемое объявление"


def test_update_post_can_remove_images(app):
    from unittest.mock import patch

    with app.app_context():
        post = create_post(
            {
                "seller_name": "Ахмад",
                "title": "С фотографиями",
                "body": "Объявление с двумя фотографиями для теста удаления.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79008880004",
                "price": 1000,
                "images": ["/media/posts/a.jpg", "/media/posts/b.jpg"],
            },
            ip_hash="remove-img",
        )
        with patch("app.services.posts.delete_stored_images") as delete_mock:
            update_post(
                post,
                {
                    "seller_name": "Ахмад",
                "title": post.title,
                    "body": post.body,
                    "category": post.category,
                    "price": post.price,
                    "images": ["/media/posts/b.jpg"],
                },
            )
            delete_mock.assert_called_once_with(["/media/posts/a.jpg"])
        assert post.images == ["/media/posts/b.jpg"]


def test_smart_query_price_range_and_category_inference():
    from app.services.smart_query import parse_search_query

    parsed = parse_search_query("квартира от 10 до 50 тыс")

    assert parsed["category"] == "nedvizhimost"
    assert parsed["price_min"] == 10000
    assert parsed["price_max"] == 50000


def test_search_ranking_prefers_exact_title_match():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from app.services.search_ranking import compute_final_score

    post = SimpleNamespace(
        title="айфон 13 pro",
        rank_score=0.5,
        created_at=datetime.now(timezone.utc),
        price=45000,
        is_promoted=False,
    )
    exact = compute_final_score(
        post,
        100,
        query="айфон",
        mode="search",
        max_text_match=100,
        price_max=50000,
    )
    vague = compute_final_score(
        post,
        100,
        query="телефон",
        mode="search",
        max_text_match=100,
        price_max=50000,
    )
    assert exact > vague


def test_hybrid_feed_sorts_by_rank_score(app):
    from unittest.mock import patch

    from app.services.search import search_posts

    with app.app_context():
        low = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Слабое объявление",
                "body": "Описание для проверки гибридного ранжирования ленты.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79009990001",
                "price": 1000,
                "images": [],
            },
            ip_hash="hybrid-low",
        )
        high = create_post(
            {
                "seller_name": "Ахмад",
                "title": "Сильное объявление",
                "body": "Описание для проверки гибридного ранжирования ленты.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79009990002",
                "price": 1000,
                "images": [],
            },
            ip_hash="hybrid-high",
        )
        high.rank_score = 0.95
        low.rank_score = 0.05
        from app.extensions import db

        db.session.commit()

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        with app.app_context():
            results, _ = search_posts(query="", sort="rank")

    assert results[0]["post"].title == "Сильное объявление"


def test_search_expanded_terms_match_brand_alias(app):
    from unittest.mock import patch

    from app.services.search import search_posts

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "Продаю iPhone 12",
                "body": "Телефон в отличном состоянии, полный комплект.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79009990003",
                "price": 40000,
                "images": [],
            },
            ip_hash="brand-alias",
        )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        with app.app_context():
            results, total = search_posts(query="айфон", sort="relevance", expanded_terms=["айфон", "iphone"])

    assert total == 1
    assert results[0]["post"].title == "Продаю iPhone 12"


def test_feed_total_matches_rendered_cards(client, app):
    from unittest.mock import patch

    with app.app_context():
        for i in range(4):
            create_post(
                {
                    "seller_name": "Ахмад",
                "title": f"Счётчик {i}",
                    "body": "Тестовое объявление для проверки совпадения счётчика и карточек.",
                    "category": "prodazha",
                    "city": "grozny",
                    "phone": f"+7900888{i:04d}",
                    "price": 1000 + i,
                    "images": [],
                },
                ip_hash=f"counter-{i}",
            )

    with patch("app.services.search._typesense_search", side_effect=RuntimeError("test")):
        res = client.get("/")

    text = res.get_data(as_text=True)
    assert res.status_code == 200
    assert "<strong>4</strong> объявлений" in text
    assert text.count("Счётчик") == 4


def test_default_sort_with_query_is_relevance(client, app):
    from unittest.mock import patch

    with patch("app.routes.main.search_posts") as search_mock:
        search_mock.return_value = ([], 0)
        client.get("/?q=айфон")

    assert search_mock.call_args.kwargs["sort"] == "relevance"


def test_sync_synonyms_builds_unique_groups():
    from app.services.search import COLLECTION_NAME, _sync_synonyms
    import app.services.search as search_module

    class FakeSynonyms:
        def __init__(self):
            self.items = []

        def upsert(self, key, payload):
            self.items.append((key, payload))

    class FakeCollection:
        def __init__(self):
            self.synonyms = FakeSynonyms()

    class FakeClient:
        def __init__(self):
            self.collections = {COLLECTION_NAME: FakeCollection()}

    fake_client = FakeClient()
    original = search_module.get_typesense_client
    search_module.get_typesense_client = lambda: fake_client
    try:
        _sync_synonyms()
        groups = [item[1]["synonyms"] for item in fake_client.collections[COLLECTION_NAME].synonyms.items]
        assert any("машина" in group and "авто" in group for group in groups)
        assert any("айфон" in group and "iphone" in group for group in groups)
    finally:
        search_module.get_typesense_client = original


def test_seed_demo_posts(app):
    from app.services.seed import clear_seed_posts, is_seeded, seed_demo_posts

    with app.app_context():
        clear_seed_posts()
        assert not is_seeded()
        count = seed_demo_posts()
        assert count == 16
        assert is_seeded()
        assert seed_demo_posts() == 0
        clear_seed_posts()
