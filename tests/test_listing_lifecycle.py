import pytest

from listings.models import PostStatusEvent
from listings.services.posts import mark_post_sold, republish_post


@pytest.mark.django_db
def test_seller_can_mark_published_post_sold_and_republish(seller, make_post):
    post = make_post(user=seller, status="published")

    mark_post_sold(post, seller)
    post.refresh_from_db()
    assert post.status == "sold"
    event = PostStatusEvent.objects.get(post=post, new_status="sold")
    assert event.actor == seller

    republish_post(post, seller)
    post.refresh_from_db()
    assert post.status == "pending"
    assert PostStatusEvent.objects.filter(post=post, new_status="pending").exists()
