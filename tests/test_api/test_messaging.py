import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from messaging.models import Conversation


@pytest.mark.django_db
def test_conversations_require_auth(api_client):
    response = api_client.get(reverse("api:conversations"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_start_conversation_and_send_message(api_client, buyer, seller, published_post):
    buyer_refresh = RefreshToken.for_user(buyer)
    seller_refresh = RefreshToken.for_user(seller)
    seller.email_verified = True
    seller.save(update_fields=["email_verified"])

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {buyer_refresh.access_token}")
    start_url = reverse("api:listing-conversation-start", kwargs={"post_id": published_post.pk})
    response = api_client.post(start_url, {"body": "Здравствуйте!"}, format="json")
    assert response.status_code == 201
    conversation_id = response.data["id"]
    assert response.data["messages"][0]["body"] == "Здравствуйте!"
    assert response.data["other_user"]["display_name"] == "Seller"

    list_response = api_client.get(reverse("api:conversations"))
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1

    seller_client = APIClient()
    seller_client.credentials(HTTP_AUTHORIZATION=f"Bearer {seller_refresh.access_token}")
    unread = seller_client.get(reverse("api:conversations-unread"))
    assert unread.status_code == 200
    assert unread.data["count"] == 1

    reply_url = reverse("api:conversation-messages", kwargs={"conversation_id": conversation_id})
    reply = seller_client.post(reply_url, {"body": "Добрый день!"}, format="json")
    assert reply.status_code == 201

    detail_url = reverse("api:conversation-detail", kwargs={"conversation_id": conversation_id})
    detail = api_client.get(detail_url)
    assert detail.status_code == 200
    assert len(detail.data["messages"]) == 2

    unread_after = api_client.get(reverse("api:conversations-unread"))
    assert unread_after.data["count"] == 0

    delete = api_client.delete(detail_url)
    assert delete.status_code == 204
    hidden = api_client.get(detail_url)
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_cannot_message_own_listing(seller_auth_client, published_post):
    url = reverse("api:listing-conversation-start", kwargs={"post_id": published_post.pk})
    response = seller_auth_client.post(url, {"body": "Привет"}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_empty_conversations_not_in_inbox(auth_client, buyer, seller, published_post):
    Conversation.objects.create(post=published_post, buyer=buyer, seller=seller)
    response = auth_client.get(reverse("api:conversations"))
    assert response.status_code == 200
    assert response.data["count"] == 0
