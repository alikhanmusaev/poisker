import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


from tests.test_api.conftest import TEST_PASSWORD


@pytest.mark.django_db
def test_register_and_login(api_client):
    payload = {
        "display_name": "Ali",
        "email": "ali@example.com",
        "phone": "+79001234567",
        "password": TEST_PASSWORD,
        "accept_terms": True,
        "accept_pdn": True,
    }
    response = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="ali@example.com")
    assert user.email_verified is False

    user.email_verified = True
    user.save(update_fields=["email_verified"])

    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": "ali@example.com", "password": TEST_PASSWORD},
        format="json",
    )
    assert login.status_code == status.HTTP_200_OK
    assert "access" in login.data["tokens"]
    assert login.data["user"]["email"] == "ali@example.com"


@pytest.mark.django_db
def test_refresh_and_me_and_logout(api_client, buyer):
    refresh = RefreshToken.for_user(buyer)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    me = api_client.get("/api/v1/auth/me/")
    assert me.status_code == status.HTTP_200_OK
    assert me.data["email"] == buyer.email

    refreshed = api_client.post(
        "/api/v1/auth/refresh/",
        {"refresh": str(refresh)},
        format="json",
    )
    assert refreshed.status_code == status.HTTP_200_OK
    assert "access" in refreshed.data
    rotated_refresh = refreshed.data.get("refresh", str(refresh))

    logout = api_client.post(
        "/api/v1/auth/logout/",
        {"refresh": rotated_refresh},
        format="json",
    )
    assert logout.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_login_requires_verified_email(api_client, seller):
    seller.email_verified = False
    seller.set_password(TEST_PASSWORD)
    seller.save(update_fields=["email_verified", "password"])
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": seller.email, "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    assert "non_field_errors" in response.data["fields"]


@pytest.mark.django_db
def test_password_reset_request(api_client, seller):
    response = api_client.post(
        "/api/v1/auth/password-reset/",
        {"email": seller.email},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data


@pytest.mark.django_db
def test_resend_verification(api_client):
    payload = {
        "display_name": "New",
        "email": "new@example.com",
        "phone": "+79001234568",
        "password": TEST_PASSWORD,
        "accept_terms": True,
        "accept_pdn": True,
    }
    api_client.post("/api/v1/auth/register/", payload, format="json")
    response = api_client.post(
        "/api/v1/auth/resend-verification/",
        {"email": "new@example.com"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data
