"""Business logic regression tests."""


def _create_post(app, phone="+79001234567", title="Тестовое объявление для проверки"):
    from app.services.posts import create_post

    with app.app_context():
        post = create_post(
            {
                "seller_name": "Продавец",
                "title": title,
                "body": "Достаточно длинное описание товара для публикации на доске.",
                "category": "prodazha",
                "city": "grozny",
                "phone": phone,
                "images": [],
            },
            ip_hash="business-logic-test",
        )
        return {
            "id": post.id,
            "edit_token": post.edit_token,
            "slug": post.slug,
            "city": post.city,
            "category": post.category,
            "title": post.title,
            "body": post.body,
        }


def test_contact_reveals_full_phone(client, app):
    post = _create_post(app, phone="+79005551234")
    res = client.get(f"/posts/{post['id']}/contact")
    data = res.get_json()

    assert res.status_code == 200
    assert data["phone"] == "+79005551234"


def test_daily_limit_survives_delete(client, app):
    post = _create_post(app, phone="+79006667788")

    with app.app_context():
        from app.models import Post
        from app.services.posts import delete_post

        delete_post(Post.query.get(post["id"]))

    res = client.post(
        "/posts/new",
        data={
            "seller_name": "Продавец",
            "title": "Второе объявление за день",
            "body": "Повторная публикация с тем же номером телефона в тот же день.",
            "category": "prodazha",
            "city": "grozny",
            "phone": "+7 (900) 666-77-88",
            "csrf_token": "test",
        },
        follow_redirects=False,
    )

    assert res.status_code == 200
    assert "уже опубликовано" in res.get_data(as_text=True)


def test_expired_post_not_public(client, app):
    from datetime import timedelta

    from app.extensions import db
    from app.models import Post, utcnow

    post = _create_post(app, phone="+79007778899", title="Истекающее объявление")
    with app.app_context():
        db_post = Post.query.get(post["id"])
        db_post.expires_at = utcnow() - timedelta(hours=1)
        db.session.commit()

    res = client.get(f"/obyavlenie/{post['city']}/{post['category']}/{post['slug']}")
    assert res.status_code == 404


def test_meta_for_hidden_post_with_token(client, app):
    from app.extensions import db
    from app.models import Post

    post = _create_post(app, phone="+79008889900", title="Скрытое объявление")
    token = post["edit_token"]
    with app.app_context():
        db_post = Post.query.get(post["id"])
        db_post.status = "hidden"
        db.session.commit()

    res = client.get(f"/posts/{post['id']}/meta?token={token}")
    data = res.get_json()

    assert res.status_code == 200
    assert data["ok"] is True
    assert data["can_edit"] is True
    assert data["status"] == "hidden"


def test_edit_allows_city_change(client, app):
    post = _create_post(app, phone="+79009990011", title="Смена города")
    token = post["edit_token"]

    res = client.post(
        f"/posts/{post['id']}/edit?token={token}",
        data={
            "title": post["title"],
            "seller_name": "Продавец",
            "body": post["body"],
            "category": "prodazha",
            "city": "gudermes",
            "csrf_token": "test",
            "token": token,
        },
        follow_redirects=True,
    )

    assert res.status_code == 200
    with app.app_context():
        from app.models import Post

        updated = Post.query.get(post["id"])
        assert updated.city == "gudermes"


def test_bumped_post_gets_freshness_boost(app):
    from datetime import timedelta

    from app.models import Post, utcnow
    from app.services.ranking import calculate_rank_score, freshness_score

    old = utcnow() - timedelta(days=10)
    bumped = utcnow() - timedelta(hours=2)
    post = Post(
        title="Bump test",
        seller_name="Seller",
        body="Body " * 20,
        category="prodazha",
        city="grozny",
        phone_hash="x",
        phone_masked="+7 *** *** 00-00",
        edit_token="token",
        status="published",
        created_at=old,
        bumped_at=bumped,
        expires_at=utcnow() + timedelta(days=20),
    )

    fresh_old_only = freshness_score(old)
    fresh_with_bump = freshness_score(old, bumped)
    assert fresh_with_bump > fresh_old_only
    assert calculate_rank_score(post) > 0
