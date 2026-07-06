"""Regression tests for production hardening."""

import re
import time


def _admin_login_csrf(client) -> str:
    res = client.get("/admin/login", base_url="https://poisker.ru")
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', res.get_data(as_text=True))
    assert match, "csrf_token missing on admin login page"
    return match.group(1)


def test_csrf_allows_www_referrer_on_admin_login(app):
    app.config.update(WTF_CSRF_ENABLED=True, WTF_CSRF_SSL_STRICT=True, APP_DOMAIN="poisker.ru")
    with app.test_client() as client:
        token = _admin_login_csrf(client)
        res = client.post(
            "/admin/login",
            data={"csrf_token": token, "username": "wrong", "password": "wrong"},
            base_url="https://poisker.ru",
            headers={"Referer": "https://www.poisker.ru/admin/login"},
        )
    assert res.status_code == 200
    assert "referrer does not match" not in res.get_data(as_text=True).lower()


def test_csrf_allows_missing_referrer_on_admin_login(app):
    app.config.update(WTF_CSRF_ENABLED=True, WTF_CSRF_SSL_STRICT=True, APP_DOMAIN="poisker.ru")
    with app.test_client() as client:
        token = _admin_login_csrf(client)
        res = client.post(
            "/admin/login",
            data={"csrf_token": token, "username": "wrong", "password": "wrong"},
            base_url="https://poisker.ru",
        )
    assert res.status_code == 200
    assert "referrer header is missing" not in res.get_data(as_text=True).lower()


def test_suggest_partial_has_no_inline_click_handler(client):
    res = client.get("/suggest?q=iphone", headers={"HX-Request": "true"})
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert "onclick=" not in text
    assert "data-suggest-value" in text or text == ""


def test_search_highlight_sanitizer_allows_only_mark_tags():
    from app.services.search import sanitize_highlight

    result = sanitize_highlight('<img src=x onerror=alert(1)><mark>iphone</mark><script>x</script>')

    assert "<mark>iphone</mark>" in result
    assert "<img" not in result
    assert "<script>" not in result


def test_security_headers_are_present(client):
    res = client.get("/")

    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in res.headers


def test_post_cards_include_hidden_owner_edit_link(client, app):
    from app.services.posts import create_post

    with app.app_context():
        post = create_post(
            {
                "seller_name": "Owner",
                "title": "Editable card",
                "body": "A post with enough body text for rendering in the feed.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79005550123",
                "images": [],
            },
            ip_hash="editable-card", publish=True,
        )
        post_id = post.id

    res = client.get("/")
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert f'data-post-id="{post_id}"' in text
    assert "data-post-card-edit" in text
    assert "Редактировать" in text


def test_app_js_initializes_post_card_edit_links():
    from pathlib import Path

    js = Path("app/static/js/app.js").read_text(encoding="utf-8")

    assert "initPostCardEditLinks" in js
    assert "editUrlForPostId" in js
    assert "/meta?token=" in js
    assert "data.can_edit" in js
    assert "hidePostCardEditLink(link)" in js


def test_hidden_attribute_cannot_be_overridden_by_button_styles():
    from pathlib import Path

    css = Path("app/static/css/style.css").read_text(encoding="utf-8")

    assert "[hidden] { display: none !important; }" in css


def test_post_json_ld_returns_dict(app):
    from types import SimpleNamespace

    from app.services.seo import post_json_ld

    post = SimpleNamespace(
        title="Test item",
        body="Body text",
        city="grozny",
        category="prodazha",
        price=1000,
    )
    with app.test_request_context("/"):
        data = post_json_ld(post, canonical_url="https://example.com/item", image_url=None)

    assert isinstance(data, dict)
    assert data["@context"] == "https://schema.org"
    assert data["@graph"][1]["name"] == "Test item"


def test_post_page_json_ld_escapes_script_breakout(client, app):
    from app.services.posts import create_post

    malicious = "</script><script>alert(1)</script>"
    with app.app_context():
        post = create_post(
            {
                "seller_name": "Seller",
                "title": malicious,
                "body": "Enough body text for the listing page to render correctly.",
                "category": "prodazha",
                "city": "grozny",
                "phone": "+79005550999",
                "images": [],
            },
            ip_hash="json-ld-xss-test", publish=True,
        )
        url = f"/obyavlenie/{post.city}/{post.category}/{post.slug}"

    res = client.get(url)
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert malicious not in text
    assert "application/ld+json" in text


def test_captcha_skipped_when_not_required(app):
    from app.services.captcha import verify_captcha

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
        assert verify_captcha("", None) is True


def test_builtin_captcha_verify(app, client):
    from app.services.captcha import verify_captcha

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = {
            "answer": "9",
            "question": "4 + 5",
            "prompt": "Сколько будет",
            "kind": "math_digits",
            "expires": time.time() + 600,
        }
        with app.app_context():
            assert verify_captcha("999") is False
        session["captcha_challenge"] = {
            "answer": "9",
            "question": "4 + 5",
            "prompt": "Сколько будет",
            "kind": "math_digits",
            "expires": time.time() + 600,
        }
        with app.app_context():
            assert verify_captcha("9") is True


def test_builtin_captcha_single_use(app, client):
    from app.services.captcha import verify_captcha

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = {
            "answer": "9",
            "question": "4 + 5",
            "prompt": "Сколько будет",
            "kind": "math_digits",
            "expires": time.time() + 600,
        }
        with app.app_context():
            assert verify_captcha("9") is True
            assert verify_captcha("9") is False


def test_security_headers_builtin_captcha_has_no_external_scripts(app, client):
    res = client.get("/")
    csp = res.headers.get("Content-Security-Policy", "")
    assert "challenges.cloudflare.com" not in csp
    assert "smartcaptcha.cloud.yandex.ru" not in csp


def test_health_endpoint(client):
    res = client.get("/health")

    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}
