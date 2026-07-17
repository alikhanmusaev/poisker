import json

import pytest
from django.test import Client


@pytest.mark.django_db
def test_manifest_served_without_redirect():
    client = Client()
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert "application/manifest+json" in response["Content-Type"]
    assert response["Cache-Control"] == "no-cache"
    data = json.loads(response.content.decode())
    assert data["display"] == "standalone"
    assert data["start_url"].startswith("/")
    assert any(icon.get("purpose") == "maskable" for icon in data["icons"])


@pytest.mark.django_db
def test_service_worker_served_without_redirect():
    client = Client()
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]
    assert response["Cache-Control"] == "no-cache"
    body = response.content.decode()
    assert "CACHE_NAME" in body
    assert "/offline" in body


@pytest.mark.django_db
def test_offline_page():
    client = Client()
    response = client.get("/offline")
    assert response.status_code == 200
    assert "Нет подключения" in response.content.decode()


@pytest.mark.django_db
def test_base_links_manifest():
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'rel="manifest"' in html
    assert "apple-mobile-web-app-capable" in html
    assert 'rel="canonical"' in html
    assert 'property="og:title"' in html
    assert "htmx.min.js?v=" in html
    assert "inter.css?v=" in html


@pytest.mark.django_db
def test_service_worker_precache_matches_versioned_assets():
    client = Client()
    sw = client.get("/sw.js").content.decode()
    assert "core.js?v=" in sw
    assert "brand/logo.png?v=" in sw
    assert "htmx.min.js?v=" in sw
    # Controlled updates: skipWaiting only via postMessage, not on install
    assert "event.data?.type === 'SKIP_WAITING'" in sw
    assert ".then(() => self.skipWaiting())" not in sw
