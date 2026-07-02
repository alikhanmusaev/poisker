"""Listing filters passed to search."""

from unittest.mock import patch


def test_with_photo_filter_passed_to_search(client):
    with patch("app.routes.main.search_posts") as search_mock:
        search_mock.return_value = ([], 0)
        res = client.get("/?with_photo=1")
        assert res.status_code == 200
        assert search_mock.call_args.kwargs["with_photo"] is True


def test_with_price_filter_passed_to_search(client):
    with patch("app.routes.main.search_posts") as search_mock:
        search_mock.return_value = ([], 0)
        res = client.get("/?with_price=1")
        assert res.status_code == 200
        assert search_mock.call_args.kwargs["with_price"] is True
