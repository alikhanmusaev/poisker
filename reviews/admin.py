from django.contrib import admin

from reviews.models import PhoneReveal, SellerReview


@admin.register(SellerReview)
class SellerReviewAdmin(admin.ModelAdmin):
    list_display = ("seller", "reviewer", "rating", "short_comment", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = (
        "seller__email",
        "seller__display_name",
        "reviewer__email",
        "reviewer__display_name",
        "comment",
    )
    raw_id_fields = ("reviewer", "seller", "conversation", "post")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Комментарий")
    def short_comment(self, obj):
        return (obj.comment or "")[:80] or "—"


@admin.register(PhoneReveal)
class PhoneRevealAdmin(admin.ModelAdmin):
    list_display = ("seller", "reviewer", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "seller__email",
        "seller__display_name",
        "reviewer__email",
        "reviewer__display_name",
    )
    raw_id_fields = ("reviewer", "seller", "post")
    readonly_fields = ("created_at",)
