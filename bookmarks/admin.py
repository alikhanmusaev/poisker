from django.contrib import admin

from bookmarks.models import CategoryBookmark, Notification, PostBookmark


@admin.register(PostBookmark)
class PostBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    raw_id_fields = ("user", "post")


@admin.register(CategoryBookmark)
class CategoryBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "created_at")
    list_filter = ("category",)
    raw_id_fields = ("user",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "title", "read_at", "created_at")
    list_filter = ("kind",)
    raw_id_fields = ("user", "post")
    search_fields = ("title", "body", "user__email")
