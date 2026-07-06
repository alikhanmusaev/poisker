"""User-facing promotion requests."""

from flask import current_app

from app.constants import PROMOTION_TYPES


def promotion_amount(promo_type: str) -> int:
    if promo_type not in PROMOTION_TYPES:
        raise ValueError("Неизвестный тип продвижения")
    base = int(current_app.config.get("PROMOTION_BOOST_24H_AMOUNT", 100))
    if promo_type == "boost_24h":
        return base
    if promo_type == "top_7d":
        return base * 5
    return base
