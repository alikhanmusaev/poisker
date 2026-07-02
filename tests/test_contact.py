"""Contact reveal endpoint and captcha gate."""

from tests.conftest import create_test_post, fill_contact_reveals, set_captcha_session


def test_contact_requires_captcha_after_soft_limit(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 5
        post = create_test_post(app, publish=True, phone="+79003334455")
        post_id = post.id

    fill_contact_reveals(client, [f"other-{i}" for i in range(5)])

    res = client.post(f"/posts/{post_id}/contact")
    data = res.get_json()

    assert res.status_code == 403
    assert data["captcha_required"] is True
    assert "phone" not in data


def test_contact_with_correct_captcha_returns_phone(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 5
        post = create_test_post(app, publish=True, phone="+79004445566")
        post_id = post.id

    fill_contact_reveals(client, [f"other-{i}" for i in range(5)])
    set_captcha_session(client, "42")

    res = client.post(f"/posts/{post_id}/contact", headers={"X-Captcha-Answer": "42"})
    data = res.get_json()

    assert res.status_code == 200
    assert data["phone"] == "+79004445566"
