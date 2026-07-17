from django.conf import settings
from django.db import models
from django.utils import timezone


class PushDevice(models.Model):
    PLATFORM_ANDROID = "android"
    PLATFORM_IOS = "ios"
    PLATFORM_CHOICES = [
        (PLATFORM_ANDROID, "Android"),
        (PLATFORM_IOS, "iOS"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    token = models.CharField(max_length=512, unique=True)
    device_id = models.CharField(max_length=64)
    platform = models.CharField(max_length=16, choices=PLATFORM_CHOICES, default=PLATFORM_ANDROID)
    app_version = models.CharField(max_length=32, blank=True, default="")
    app_build = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True, db_index=True)
    failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_id"],
                name="notifications_pushdevice_user_device_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "active"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform}:{self.device_id[:8]}… ({'on' if self.active else 'off'})"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    messages_enabled = models.BooleanField(default=True)
    listings_enabled = models.BooleanField(default=True)
    system_enabled = models.BooleanField(default=True)
    marketing_enabled = models.BooleanField(
        default=False,
        help_text="Маркетинг выключен по умолчанию и требует отдельного согласия.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"prefs:{self.user_id}"
