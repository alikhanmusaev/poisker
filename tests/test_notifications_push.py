import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.models import NotificationPreference, PushDevice
from notifications.payloads import sanitize_push_url
from notifications.services import deactivate_device, register_device, send_push

User = get_user_model()


@pytest.mark.django_db
def test_sanitize_push_url_allows_poisker():
    assert sanitize_push_url("https://poisker.ru/messages/1/") == "https://poisker.ru/messages/1/"
    assert sanitize_push_url("https://evil.example/x") == "https://poisker.ru/"
    assert sanitize_push_url("http://poisker.ru/") == "https://poisker.ru/"


@pytest.mark.django_db
def test_register_device_and_rebind(seller):
    d1 = register_device(
        user=seller,
        token="token-aaa",
        device_id="device-1",
        app_version="1.0",
        app_build=1,
    )
    assert d1.active
    other = User.objects.create_user(
        email="other-push@example.com",
        password="password12345",
        display_name="Other",
        phone="+79009998877",
    )
    d2 = register_device(user=other, token="token-aaa", device_id="device-2")
    assert d2.user_id == other.id
    assert not PushDevice.objects.filter(user=seller, token="token-aaa").exists()


@pytest.mark.django_db
def test_deactivate_device(seller):
    register_device(user=seller, token="tok", device_id="dev-x")
    assert deactivate_device(user=seller, device_id="dev-x")
    assert not PushDevice.objects.get(user=seller, device_id="dev-x").active


@pytest.mark.django_db
def test_push_devices_api_session(seller):
    client = Client(enforce_csrf_checks=False)
    client.force_login(seller)
    url = reverse("api:notifications:device-register")
    response = client.post(
        url,
        data={
            "token": "fcm-test-token",
            "platform": "android",
            "device_id": "uuid-1",
            "app_version": "1.0",
            "app_build": 1,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    assert PushDevice.objects.filter(user=seller, device_id="uuid-1", active=True).exists()

    delete_url = reverse("api:notifications:device-current")
    deleted = client.delete(f"{delete_url}?device_id=uuid-1")
    assert deleted.status_code == 200
    assert not PushDevice.objects.get(user=seller, device_id="uuid-1").active


@pytest.mark.django_db
def test_push_devices_api_jwt(seller):
    api = APIClient()
    token = RefreshToken.for_user(seller)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    response = api.post(
        reverse("api:notifications:device-register"),
        {
            "token": "jwt-fcm-token",
            "platform": "android",
            "device_id": "jwt-device",
            "app_version": "1.0",
            "app_build": 1,
        },
        format="json",
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_preferences_default_marketing_off(seller):
    pref = NotificationPreference.objects.create(user=seller)
    assert pref.messages_enabled
    assert not pref.marketing_enabled


@pytest.mark.django_db
def test_send_push_skips_without_firebase(seller, settings):
    settings.FCM_ENABLED = False
    register_device(user=seller, token="t", device_id="d")
    result = send_push(
        seller,
        title="t",
        body="b",
        url="https://poisker.ru/",
        notification_type="system",
    )
    assert result["skipped"] == 1
    assert result["sent"] == 0
