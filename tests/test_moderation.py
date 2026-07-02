"""Post moderation workflow tests."""

from tests.conftest import create_test_post, make_post_payload


def test_create_post_defaults_to_pending(app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79001001001")
        assert post.status == "pending"


def test_pending_post_is_not_public(client, app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79001001002")
        post_id = post.id
        token = post.edit_token
    assert client.get(f"/posts/{post_id}").status_code == 404
    res = client.get(f"/posts/{post_id}?token={token}")
    assert res.status_code == 200
    assert "на модерации" in res.get_data(as_text=True).lower()


def test_admin_publish_makes_post_public(client, app):
    from app.models import AdminUser, Post
    from app.extensions import db

    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79001001003")
        post_id = post.id
        admin = AdminUser(username="moderator")
        admin.set_password("modpass")
        db.session.add(admin)
        db.session.commit()

    client.post("/admin/login", data={"username": "moderator", "password": "modpass"}, follow_redirects=True)
    res = client.post(f"/admin/posts/{post_id}/publish", follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        refreshed = db.session.get(Post, post_id)
        assert refreshed.status == "published"

    assert client.get(f"/posts/{post_id}").status_code in (200, 301)


def test_create_post_ajax_returns_moderation_flag(client):
    res = client.post(
        "/posts/new",
        data=make_post_payload(phone="+79001001004"),
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        },
    )
    data = res.get_json()
    assert res.status_code == 200
    assert data["ok"] is True
    assert data["status"] == "pending"
    assert data["moderation_pending"] is True
