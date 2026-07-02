"""Production readiness: filters, captcha, soft delete, contact flow."""

import time
from io import BytesIO
from unittest.mock import patch

import pytest

from tests.conftest import create_test_post, make_post_payload


def _set_captcha_answer(client, answer: str):
    with client.session_transaction() as sess:
        sess["captcha_challenge"] = {
            "answer": answer,
            "question": "test",
            "prompt": "Проверка",
            "kind": "math_digits",
            "expires": time.time() + 600,
        }


def test_create_post_success(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
    res = client.post("/posts/new", data=make_post_payload(phone="+79002000001"))
    assert res.status_code in (200, 302)


def test_create_post_rejects_short_title(client, app):
    from app.models import Post

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
        before = Post.query.count()
    payload = make_post_payload(phone="+79002000002")
    payload["title"] = "abc"
    res = client.post("/posts/new", data=payload)
    assert res.status_code == 200
    with app.app_context():
        assert Post.query.count() == before


def test_create_post_rejects_short_body(client, app):
    from app.models import Post

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
        before = Post.query.count()
    payload = make_post_payload(phone="+79002000003")
    payload["body"] = "коротко"
    res = client.post("/posts/new", data=payload)
    assert res.status_code == 200
    with app.app_context():
        assert Post.query.count() == before


def test_create_post_rejects_long_title(client, app):
    from app.models import Post

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
        before = Post.query.count()
    payload = make_post_payload(phone="+79002000015")
    payload["title"] = "А" * 101
    res = client.post("/posts/new", data=payload)
    assert res.status_code == 200
    with app.app_context():
        assert Post.query.count() == before


def test_create_post_rejects_long_body(client, app):
    from app.models import Post

    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = False
        before = Post.query.count()
    payload = make_post_payload(phone="+79002000016")
    payload["body"] = "Описание объявления. " * 200
    res = client.post("/posts/new", data=payload)
    assert res.status_code == 200
    with app.app_context():
        assert Post.query.count() == before


def test_edit_post_with_valid_token(client, app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000004")
        post_id = post.id
        token = post.edit_token
    res = client.get(f"/posts/{post_id}/edit?token={token}")
    assert res.status_code == 200


def test_edit_post_without_token_404(client, app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000005")
        post_id = post.id
    assert client.get(f"/posts/{post_id}/edit").status_code == 404


def test_soft_delete_sets_status_deleted(client, app):
    from app.models import Post
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000006")
        post_id = post.id
        delete_post(post)
        refreshed = Post.query.get(post_id)
        assert refreshed.status == "deleted"
        assert refreshed.deleted_at is not None


def test_deleted_post_not_public(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000007")
        post_id = post.id
        city = post.city
        category = post.category
        slug = post.slug
        delete_post(post)
    assert client.get(f"/posts/{post_id}").status_code == 404
    assert client.get(f"/obyavlenie/{city}/{category}/{slug}").status_code == 404


def test_meta_deleted_post_returns_deleted_flag(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000014")
        post_id = post.id
        token = post.edit_token
        delete_post(post)
    res = client.get(f"/posts/{post_id}/meta?token={token}")
    assert res.status_code == 410
    assert res.get_json().get("deleted") is True


def test_listing_with_photo_filter_passed_to_search(client, app):
    with patch("app.routes.main.search_posts") as search_mock:
        search_mock.return_value = ([], 0)
        client.get("/?with_photo=1")
        assert search_mock.call_args.kwargs["with_photo"] is True


def test_listing_with_price_filter_passed_to_search(client, app):
    with patch("app.routes.main.search_posts") as search_mock:
        search_mock.return_value = ([], 0)
        client.get("/?with_price=yes")
        assert search_mock.call_args.kwargs["with_price"] is True


def test_upload_rejects_non_image(client, app):
    from app.services.storage import upload_image
    from werkzeug.datastructures import FileStorage

    with app.app_context():
        bad = FileStorage(stream=BytesIO(b"not an image"), filename="file.txt", content_type="text/plain")
        with pytest.raises(ValueError, match="формат"):
            upload_image(bad)


def test_sitemap_excludes_deleted_posts(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002000008")
        url = f"/obyavlenie/{post.city}/{post.category}/{post.slug}"
        delete_post(post)
    text = client.get("/sitemap.xml").get_data(as_text=True)
    assert url not in text


def test_builtin_captcha_has_question(app):
    from app.services.captcha import ensure_captcha_challenge, generate_builtin_challenge

    challenge = generate_builtin_challenge()
    assert challenge["question"]
    assert challenge["answer"]
    with app.test_request_context("/"):
        question = ensure_captcha_challenge(force_new=True)
        assert isinstance(question, str)
        assert len(question) > 0


def test_builtin_captcha_correct_answer(app, client):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
    _set_captcha_answer(client, "12")
    with client.session_transaction() as sess:
        challenge = sess["captcha_challenge"]
    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = challenge
        with app.app_context():
            from app.services.captcha import verify_captcha

            assert verify_captcha("12") is True


def test_builtin_captcha_wrong_answer(app, client):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
    _set_captcha_answer(client, "12")
    with client.session_transaction() as sess:
        challenge = sess["captcha_challenge"]
    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = challenge
        with app.app_context():
            from app.services.captcha import verify_captcha

            assert verify_captcha("99") is False


def test_builtin_captcha_single_use(app, client):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
    _set_captcha_answer(client, "7")
    with client.session_transaction() as sess:
        challenge = sess["captcha_challenge"]
    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = challenge
        with app.app_context():
            from app.services.captcha import verify_captcha

            assert verify_captcha("7") is True
            assert verify_captcha("7") is False


def test_builtin_captcha_expired_fails(app, client):
    from app.services.captcha import verify_captcha

    with app.test_request_context("/"):
        from flask import session

        session["captcha_challenge"] = {
            "answer": "5",
            "question": "2 + 3",
            "prompt": "Сколько будет",
            "kind": "math_digits",
            "expires": time.time() - 1,
        }
        with app.app_context():
            app.config["REQUIRE_CAPTCHA"] = True
            assert verify_captcha("5") is False


def test_contact_without_captcha_within_soft_limit(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 5
        post = create_test_post(app, publish=True, phone="+79002000009")
        post_id = post.id
    res = client.post(f"/posts/{post_id}/contact")
    assert res.status_code == 200
    assert res.get_json()["phone"]


def test_contact_requires_captcha_after_soft_limit(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 0
        post = create_test_post(app, publish=True, phone="+79002000010")
        post_id = post.id
    res = client.post(f"/posts/{post_id}/contact")
    data = res.get_json()
    assert res.status_code == 403
    assert data["captcha_required"] is True
    assert data.get("captcha_question")


def test_contact_wrong_captcha_no_phone(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 0
        post = create_test_post(app, publish=True, phone="+79002000011")
        post_id = post.id
    res = client.post(f"/posts/{post_id}/contact", data={"captcha_answer": "wrong"})
    data = res.get_json()
    assert "phone" not in data
    assert data.get("captcha_required") is True


def test_contact_correct_captcha_returns_phone(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 0
        post = create_test_post(app, publish=True, phone="+79002000012")
        post_id = post.id
    _set_captcha_answer(client, "42")
    res = client.post(f"/posts/{post_id}/contact", data={"captcha_answer": "42"})
    assert res.status_code == 200
    assert res.get_json()["phone"]


def test_contact_repeat_same_post_no_extra_captcha(client, app):
    with app.app_context():
        app.config["REQUIRE_CAPTCHA"] = True
        app.config["CONTACT_SOFT_LIMIT"] = 0
        post = create_test_post(app, publish=True, phone="+79002000013")
        post_id = post.id
    _set_captcha_answer(client, "11")
    client.post(f"/posts/{post_id}/contact", data={"captcha_answer": "11"})
    res = client.post(f"/posts/{post_id}/contact")
    assert res.status_code == 200
    assert res.get_json()["phone"]
