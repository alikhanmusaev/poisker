from django.test import Client, RequestFactory, override_settings
from django.urls import reverse


@override_settings(DEBUG=False)
def test_missing_listing_renders_branded_404():
    client = Client()
    response = client.get(
        "/obyavlenie/grozny/uslugi/prokat-arenda-stolov-stulev-fotozon-arok-i-shat-grozny/"
        "fe635232-bab9-4aac-ab15-01845d679a3d/"
    )
    assert response.status_code == 404
    body = response.content.decode()
    assert "Страница не найдена" in body
    assert "Not Found" not in body
    assert reverse("core:index") in body


@override_settings(DEBUG=False)
def test_unknown_path_renders_branded_404():
    client = Client()
    response = client.get("/net-takoy-stranicy/")
    assert response.status_code == 404
    assert "Страница не найдена" in response.content.decode()


def test_error_handlers_render_expected_status_and_copy():
    from core.views import bad_request, page_not_found, permission_denied, server_error

    request = RequestFactory().get("/")
    not_found = page_not_found(request, Exception("missing"))
    forbidden = permission_denied(request, Exception("denied"))
    bad = bad_request(request, Exception("bad"))
    crash = server_error(request)

    assert not_found.status_code == 404
    assert "Страница не найдена" in not_found.content.decode()
    assert forbidden.status_code == 403
    assert "Нет доступа" in forbidden.content.decode()
    assert bad.status_code == 400
    assert "Некорректный запрос" in bad.content.decode()
    assert crash.status_code == 500
    assert "На сервере произошла ошибка" in crash.content.decode()
