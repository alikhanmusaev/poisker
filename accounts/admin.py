from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "display_name",
        "phone",
        "rating_avg",
        "rating_count",
        "is_blocked",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_blocked", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "display_name", "phone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Профиль", {"fields": ("display_name", "phone", "phone_digits", "phone_verified")}),
        ("Рейтинг", {"fields": ("rating_avg", "rating_count")}),
        ("Статус", {"fields": ("is_blocked", "is_active", "is_staff", "is_superuser")}),
        ("Права", {"fields": ("groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "date_joined", "created_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )
    readonly_fields = (
        "created_at",
        "date_joined",
        "last_login",
        "phone_digits",
        "rating_avg",
        "rating_count",
    )
