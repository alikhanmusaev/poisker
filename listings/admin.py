from django.contrib import admin

from listings.models import Post, Promotion, Report
from moderation.services import approve_post, hide_post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "settlement", "city", "status", "price", "created_at")
    list_filter = ("status", "category", "settlement__region", "settlement", "has_photo")
    search_fields = ("title", "body", "user__email", "user__display_name", "settlement__name", "city")
    readonly_fields = ("created_at", "updated_at", "views", "contact_clicks", "reports_count")
    raw_id_fields = ("user",)
    autocomplete_fields = ("settlement",)
    list_select_related = ("user", "settlement", "settlement__region")
    actions = ["publish_posts", "hide_posts"]

    @admin.action(description="Опубликовать")
    def publish_posts(self, request, queryset):
        for post in queryset:
            approve_post(post, request.user)

    @admin.action(description="Скрыть")
    def hide_posts(self, request, queryset):
        for post in queryset.filter(status="published"):
            hide_post(post, request.user)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("post", "reason", "status", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("post__title", "comment")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("post", "type", "amount", "status", "created_at")
    list_filter = ("status", "type")
