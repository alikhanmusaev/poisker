"""Post lifecycle: daily limit, soft delete, public visibility."""

import pytest

from tests.conftest import create_test_post, make_post_payload


def test_soft_delete_does_not_release_daily_limit(app):
    from app.services.posts import PostLimitError, create_post, delete_post
    from app.services.phone import hash_phone, validate_phone

    phone = "+79001112233"
    phone_hash = hash_phone(validate_phone(phone))

    with app.app_context():
        post = create_test_post(app, publish=True, phone=phone)
        delete_post(post)

        for number in range(2, 6):
            create_post(
                make_post_payload(phone=phone, title=f"Объявление номер {number}"),
                ip_hash="limit-test",
                publish=True,
            )

        with pytest.raises(PostLimitError):
            create_post(make_post_payload(phone=phone, title="Шестое за сутки"), ip_hash="limit-test", publish=True)


def test_deleted_post_not_public(app):
    from app.services.posts import (
        delete_post,
        get_post_by_token,
        get_public_post,
        get_viewable_post,
    )

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79002223344")
        post_id = post.id
        token = post.edit_token

        delete_post(post)

        assert get_public_post(post_id) is None
        assert get_viewable_post(post_id) is None
        assert get_viewable_post(post_id, token=token) is None
        assert get_post_by_token(post_id, token) is None
