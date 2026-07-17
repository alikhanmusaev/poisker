from django.contrib import admin

from notifications.models import NotificationPreference, PushDevice


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "platform",
        "device_id",
        "active",
        "failure_count",
        "app_version",
        "last_seen_at",
    )
    list_filter = ("platform", "active")
    search_fields = ("device_id", "user__email", "user__display_name")
    readonly_fields = ("created_at", "updated_at", "last_seen_at")
    # Never expose full FCM token in list view.
    exclude = ("token",)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "messages_enabled",
        "listings_enabled",
        "system_enabled",
        "marketing_enabled",
        "updated_at",
    )
    search_fields = ("user__email", "user__display_name")
