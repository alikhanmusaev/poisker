import pytest

from listings.services.posts import update_post


@pytest.mark.django_db
def test_published_image_changes_wait_for_moderation(make_post, seller, staff_user, city_slug):
    post = make_post(
        user=seller,
        status="published",
        images=["/media/posts/old.jpg"],
        has_photo=True,
        cover_index=0,
    )
    update_post(
        post,
        seller,
        {
            "title": post.title,
            "body": post.body,
            "category": post.category,
            "city": city_slug,
            "condition": post.condition,
            "price": post.price,
            "cover_index": 0,
        },
        image_keys=["/media/posts/new.jpg"],
    )
    post.refresh_from_db()
    assert post.images == ["/media/posts/old.jpg"]
    assert post.pending_revision["images"] == ["/media/posts/new.jpg"]

    from moderation.services import approve_post

    approve_post(post, staff_user)
    post.refresh_from_db()
    assert post.images == ["/media/posts/new.jpg"]
    assert post.pending_revision is None
