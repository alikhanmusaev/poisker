"""Regression tests for production hardening."""


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
            ip_hash="editable-card",
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
