from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from listings.models import Post
from tests.test_api.conftest import TEST_PASSWORD


def _img_file(name="photo.jpg"):
    buf = BytesIO()
    Image.new("RGB", (400, 300), (120, 40, 40)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


@pytest.mark.django_db
def test_categories_and_cities(api_client):
    categories = api_client.get("/api/v1/categories/")
    assert categories.status_code == status.HTTP_200_OK
    assert len(categories.data) == 17
    assert categories.data[0]["slug"]

    cities = api_client.get("/api/v1/cities/", {"search": "гроз"})
    assert cities.status_code == status.HTTP_200_OK
    assert any(item["slug"] == "grozny" for item in cities.data)


@pytest.mark.django_db
def test_public_list_only_published(api_client, make_post, seller, city_slug):
    make_post(status="pending")
    published = make_post(
        status="published",
        published_at=timezone.now(),
        ever_published=True,
    )
    response = api_client.get("/api/v1/listings/")
    assert response.status_code == status.HTTP_200_OK
    ids = {item["id"] for item in response.data["results"]}
    assert str(published.id) in ids
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_listing_detail_and_contact(auth_client, published_post, seller):
    detail = auth_client.get(f"/api/v1/listings/{published_post.id}/")
    assert detail.status_code == status.HTTP_200_OK
    assert detail.data["seller"]["display_name"] == seller.display_name

    contact = auth_client.post(f"/api/v1/listings/{published_post.id}/contact/")
    assert contact.status_code == status.HTTP_200_OK
    assert contact.data["phone"]


@pytest.mark.django_db
@patch("api.images.upload_image")
def test_create_update_delete_listing(mock_upload, auth_client, seller, city_slug):
    mock_upload.return_value = "/media/posts/test.jpg"

    create = auth_client.post(
        "/api/v1/listings/",
        {
            "title": "Продам телефон",
            "body": "Отличное состояние, полный комплект, без царапин.",
            "category": "elektronika",
            "city": city_slug,
            "condition": "used",
            "price": "15000",
            "images": _img_file(),
        },
        format="multipart",
    )
    assert create.status_code == status.HTTP_201_CREATED
    post_id = create.data["id"]
    assert Post.objects.get(pk=post_id).status == "pending"

    other_client = APIClient()
    refresh = RefreshToken.for_user(seller)
    other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    forbidden = other_client.patch(
        f"/api/v1/listings/{post_id}/",
        {"title": "Взлом"},
        format="json",
    )
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN

    update = auth_client.patch(
        f"/api/v1/listings/{post_id}/",
        {"title": "Продам смартфон"},
        format="json",
    )
    assert update.status_code == status.HTTP_200_OK
    assert update.data["title"] == "Продам смартфон"


@pytest.mark.django_db
def test_my_listings(seller_auth_client, make_post, seller):
    make_post(status="draft")
    response = seller_auth_client.get("/api/v1/me/listings/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_bookmarks(auth_client, buyer, published_post):
    add = auth_client.post(f"/api/v1/listings/{published_post.id}/bookmark/")
    assert add.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    listing = auth_client.get("/api/v1/listings/")
    item = next(i for i in listing.data["results"] if i["id"] == str(published_post.id))
    assert item["is_bookmarked"] is True

    bookmarks = auth_client.get("/api/v1/me/bookmarks/")
    assert bookmarks.status_code == status.HTTP_200_OK
    assert bookmarks.data["count"] == 1

    remove = auth_client.delete(f"/api/v1/listings/{published_post.id}/bookmark/")
    assert remove.status_code == status.HTTP_204_NO_CONTENT

    add2 = auth_client.post(f"/api/v1/listings/{published_post.id}/bookmark/")
    assert add2.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_report_listing(api_client, buyer, seller, published_post):
    seller.email_verified = True
    seller.set_password(TEST_PASSWORD)
    seller.save(update_fields=["email_verified", "password"])

    url = f"/api/v1/listings/{published_post.id}/report/"

    seller_client = APIClient()
    seller_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(seller).access_token}"
    )
    own = seller_client.post(url, {"reason": "spam"}, format="json")
    assert own.status_code == status.HTTP_400_BAD_REQUEST

    buyer_client = APIClient()
    buyer_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(buyer).access_token}"
    )
    ok = buyer_client.post(
        url,
        {"reason": "spam", "comment": "Похоже на мошенничество"},
        format="json",
    )
    assert ok.status_code == status.HTTP_201_CREATED

    again = buyer_client.post(url, {"reason": "fraud"}, format="json")
    assert again.status_code == status.HTTP_400_BAD_REQUEST
