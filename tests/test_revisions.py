"""Revision moderation, cover image, SEO category routes."""

from tests.conftest import create_test_post, make_post_payload


def test_update_title_goes_to_pending_revision_without_unpublishing(app):
    from app.services.posts import update_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002001")
        original_title = post.title
        original_body = post.body
        update_post(
            post,
            {
                "title": "Новый заголовок объявления",
                "body": post.body,
                "seller_name": post.seller_name,
                "category": post.category,
                "city": post.city,
                "price": post.price,
                "images": list(post.images or []),
                "cover_index": 0,
            },
        )
        assert post.status == "published"
        assert post.title == original_title
        assert post.body == original_body
        assert post.pending_revision is not None
        assert post.pending_revision["title"] == "Новый заголовок объявления"


def test_update_price_applies_immediately(app):
    from app.services.posts import update_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002002", price=1000)
        update_post(
            post,
            {
                "title": post.title,
                "body": post.body,
                "seller_name": post.seller_name,
                "category": post.category,
                "city": post.city,
                "price": 2500,
                "images": list(post.images or []),
                "cover_index": 0,
            },
        )
        assert post.price == 2500
        assert post.pending_revision is None


def test_apply_pending_revision_updates_live_content(app):
    from app.models import Post
    from app.services.posts import apply_pending_revision, update_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002003")
        update_post(
            post,
            {
                "title": "Заголовок после правки",
                "body": "Описание после правки, достаточно длинное для проверки.",
                "seller_name": post.seller_name,
                "category": post.category,
                "city": post.city,
                "price": post.price,
                "images": list(post.images or []),
                "cover_index": 0,
            },
        )
        post_id = post.id
        apply_pending_revision(post)

        refreshed = Post.query.get(post_id)
        assert refreshed.pending_revision is None
        assert refreshed.title == "Заголовок после правки"
        assert "после правки" in refreshed.body


def test_ordered_images_puts_cover_first(app):
    from app.utils.post_display import ordered_images

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002004")
        post.images = ["/media/a.jpg", "/media/b.jpg", "/media/c.jpg"]
        post.cover_index = 2
        assert ordered_images(post) == ["/media/c.jpg", "/media/a.jpg", "/media/b.jpg"]


def test_category_page_is_seo_friendly(client):
    res = client.get("/avto/")
    assert res.status_code == 200
    assert "Авто" in res.get_data(as_text=True)


def test_index_category_query_redirects_to_category_page(client):
    res = client.get("/?category=avto", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers["Location"].endswith("/avto/")


def test_user_promote_route(client, app):
    from app.models import Promotion

    app.config["PROMOTIONS_ENABLED"] = True

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002005")
        post_id = post.id
        token = post.edit_token

    res = client.get(f"/posts/{post_id}/promote?token={token}")
    assert res.status_code == 200
    assert "Продвижение объявления" in res.get_data(as_text=True)

    res = client.post(
        f"/posts/{post_id}/promote?token={token}",
        data={"token": token, "type": "boost_24h"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    with app.app_context():
        promo = Promotion.query.filter_by(post_id=post_id, status="pending").first()
        assert promo is not None
        assert promo.type == "boost_24h"


def test_user_promotions_are_disabled_by_default(client, app):
    from app.models import Promotion

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002006")
        post_id = post.id
        token = post.edit_token

    edit_res = client.get(f"/posts/{post_id}/edit?token={token}")
    assert edit_res.status_code == 200
    assert "/promote" not in edit_res.get_data(as_text=True)

    get_res = client.get(f"/posts/{post_id}/promote?token={token}")
    post_res = client.post(
        f"/posts/{post_id}/promote?token={token}",
        data={"token": token, "type": "boost_24h"},
    )
    assert get_res.status_code == 404
    assert post_res.status_code == 404
    with app.app_context():
        assert Promotion.query.filter_by(post_id=post_id).count() == 0


def test_reject_pending_revision_keeps_live_content(app):
    from app.services.posts import reject_pending_revision, update_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002007")
        original_title = post.title
        update_post(
            post,
            {
                "title": "Отклонённая правка заголовка",
                "body": post.body,
                "seller_name": post.seller_name,
                "category": post.category,
                "city": post.city,
                "price": post.price,
                "images": list(post.images or []),
                "cover_index": 0,
            },
        )
        assert post.pending_revision is not None
        reject_pending_revision(post)
        assert post.pending_revision is None
        assert post.title == original_title


def test_admin_approve_revision(client, app):
    from app.extensions import db
    from app.models import AdminUser, Post
    from app.services.posts import update_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79001002006")
        update_post(
            post,
            {
                "title": "Правка для админки",
                "body": post.body,
                "seller_name": post.seller_name,
                "category": post.category,
                "city": post.city,
                "price": post.price,
                "images": list(post.images or []),
                "cover_index": 0,
            },
        )
        post_id = post.id
        admin = AdminUser(username="revadmin")
        admin.set_password("revpass")
        db.session.add(admin)
        db.session.commit()

    client.post("/admin/login", data={"username": "revadmin", "password": "revpass"}, follow_redirects=True)
    res = client.post(f"/admin/posts/{post_id}/approve-revision", follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        refreshed = db.session.get(Post, post_id)
        assert refreshed.title == "Правка для админки"
        assert refreshed.pending_revision is None
