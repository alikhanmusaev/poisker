"""Tests for search suggestions."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.posts import create_post


def test_suggest_skips_useless_photo_and_price_refinements(app):
    from app.services.search import suggest

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "iPhone 13 без фото",
                "body": "Телефон apple iphone в хорошем состоянии.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110001",
                "price": 45000,
                "images": [],
            },
            ip_hash="suggest-a",
        )

        items = suggest("iphone")

    assert "iphone до 50000" not in items
    assert "iphone с фото" not in items


def test_suggest_offers_photo_refinement_when_useful(app):
    from app.services.search import suggest

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "iPhone с фото",
                "body": "Apple iphone, есть фотографии.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110002",
                "price": 40000,
                "images": ["/media/posts/a.jpg"],
            },
            ip_hash="suggest-b",
        )
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "iPhone без фото",
                "body": "Apple iphone, фото нет.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110003",
                "price": 35000,
                "images": [],
            },
            ip_hash="suggest-c",
        )

        items = suggest("iphone")

    assert "iphone с фото" in items


def test_suggest_offers_price_refinement_when_useful(app):
    from app.services.search import suggest

    with app.app_context():
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "iPhone дешёвый",
                "body": "Apple iphone недорого.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110004",
                "price": 30000,
                "images": [],
            },
            ip_hash="suggest-d",
        )
        create_post(
            {
                "seller_name": "Ахмад",
                "title": "iPhone дорогой",
                "body": "Apple iphone pro max.",
                "category": "elektronika",
                "city": "grozny",
                "phone": "+79001110005",
                "price": 90000,
                "images": [],
            },
            ip_hash="suggest-e",
        )

        items = suggest("iphone")

    assert any(item.startswith("iphone до ") for item in items)
    assert "iphone до 30000" in items
