"""SEO: 410 Gone for removed/expired posts, sitemap visibility."""

from datetime import timedelta

from tests.conftest import create_test_post


def _public_url(post):
    return f"/obyavlenie/{post.city}/{post.category}/{post.slug}"


def test_published_post_returns_200(client, app):
    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110001")
        url = _public_url(post)

    res = client.get(url)
    assert res.status_code == 200
    assert "noindex" not in res.get_data(as_text=True).lower()


def test_deleted_post_by_slug_returns_410(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110002")
        url = _public_url(post)
        title = post.title
        delete_post(post)

    res = client.get(url)
    assert res.status_code == 410
    text = res.get_data(as_text=True)
    assert "Объявление больше недоступно" in text
    assert 'content="noindex, nofollow"' in text
    assert title not in text


def test_expired_post_by_slug_returns_410(client, app):
    from app.extensions import db
    from app.models import utcnow

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110003")
        url = _public_url(post)
        post.expires_at = utcnow() - timedelta(hours=1)
        db.session.commit()

    res = client.get(url)
    assert res.status_code == 410


def test_hidden_post_without_token_returns_404(client, app):
    from app.extensions import db

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110004")
        url = _public_url(post)
        post.status = "hidden"
        db.session.commit()

    assert client.get(url).status_code == 404


def test_pending_post_without_token_returns_404(client, app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79001110005")
        url = _public_url(post)

    assert client.get(url).status_code == 404


def test_pending_post_with_owner_token_returns_200(client, app):
    with app.app_context():
        post = create_test_post(app, publish=False, phone="+79001110006")
        url = _public_url(post)
        token = post.edit_token

    res = client.get(f"{url}?token={token}")
    assert res.status_code == 200
    assert "на модерации" in res.get_data(as_text=True).lower()


def test_hidden_post_with_owner_token_returns_200(client, app):
    from app.extensions import db

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110007")
        url = _public_url(post)
        token = post.edit_token
        post.status = "hidden"
        db.session.commit()

    res = client.get(f"{url}?token={token}")
    assert res.status_code == 200


def test_deleted_post_with_owner_token_returns_410(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110008")
        url = _public_url(post)
        token = post.edit_token
        post_id = post.id
        delete_post(post)

    assert client.get(f"{url}?token={token}").status_code == 410
    assert client.get(f"/posts/{post_id}?token={token}").status_code == 410


def test_sitemap_excludes_expired_post(client, app):
    from app.extensions import db
    from app.models import utcnow

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110009")
        url = _public_url(post)
        slug = post.slug
        post.expires_at = utcnow() - timedelta(days=1)
        db.session.commit()

    text = client.get("/sitemap.xml").get_data(as_text=True)
    assert url not in text
    assert slug not in text


def test_sitemap_excludes_deleted_post(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110010")
        url = _public_url(post)
        delete_post(post)

    text = client.get("/sitemap.xml").get_data(as_text=True)
    assert url not in text


def test_admin_preview_deleted_post_returns_200(client, app):
    from app.services.posts import delete_post
    from tests.test_admin import _login_admin

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001110011")
        post_id = post.id
        delete_post(post)

    _login_admin(client, app)
    res = client.get(f"/admin/posts/{post_id}/preview")
    assert res.status_code == 200
    assert "Админ-предпросмотр" in res.get_data(as_text=True)
