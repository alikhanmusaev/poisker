import re

import django.core.validators
from django.core.exceptions import ValidationError


def normalize_phone(phone: str) -> str:
    digits = phone_digits(phone)
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return (phone or "").strip()


def phone_digits(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    return digits


def validate_phone(value: str) -> str:
    digits = phone_digits(value)
    if len(digits) < 11:
        raise ValidationError("Укажите полный номер телефона.")
    normalized = normalize_phone(value)
    if len(phone_digits(normalized)) < 11:
        raise ValidationError("Укажите корректный номер телефона.")
    return normalized


def ensure_phone_available(phone: str, *, exclude_user_id=None):
    from accounts.models import User

    normalized = validate_phone(phone)
    digits = phone_digits(normalized)
    qs = User.objects.filter(phone_digits=digits)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    if qs.exists():
        raise ValidationError("Этот номер уже используется другим аккаунтом.")
    return normalized


phone_validator = django.core.validators.RegexValidator(
    regex=r"^\+?\d",
    message="Укажите корректный номер телефона.",
)
