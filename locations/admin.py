from django.contrib import admin
from django.db.models import Count, ProtectedError
from django.contrib import messages

from locations.models import Region, Settlement


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "settlements_count")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "code")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_settlements_count=Count("settlements"))

    @admin.display(description="НП", ordering="_settlements_count")
    def settlements_count(self, obj):
        return obj._settlements_count

    def delete_model(self, request, obj):
        try:
            super().delete_model(request, obj)
        except ProtectedError:
            messages.error(
                request,
                "Нельзя удалить регион: есть связанные населённые пункты или объявления.",
            )

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return super().has_delete_permission(request, obj)
        if obj.settlements.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "region",
        "type",
        "population",
        "is_popular",
        "is_active",
        "ads_count",
        "slug",
    )
    list_filter = ("is_active", "is_popular", "region")
    search_fields = ("name", "slug", "geoname_id")
    autocomplete_fields = ("region",)
    list_select_related = ("region",)
    ordering = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_ads_count=Count("ads"))

    @admin.display(description="Объявления", ordering="_ads_count")
    def ads_count(self, obj):
        return obj._ads_count

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return super().has_delete_permission(request, obj)
        if obj.ads.exists():
            return False
        return super().has_delete_permission(request, obj)
