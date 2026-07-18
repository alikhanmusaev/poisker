from rest_framework import serializers

from accounts.models import User
from api.serializers.auth import PublicSellerSerializer
from api.utils import absolute_url, absolute_urls
from core.templatetags.poisker_tags import format_price
from listings.constants import CATEGORY_LABELS, CITIES, CONDITION_LABELS, POST_STATUS_LABELS, REPORT_REASONS
from listings.models import Post
from listings.services.seo_urls import post_public_url
from listings.utils.post_display import ordered_images


class ListingListSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    city_label = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "category",
            "category_label",
            "city",
            "city_label",
            "condition",
            "price",
            "price_display",
            "status",
            "has_photo",
            "cover_image",
            "views",
            "created_at",
            "expires_at",
            "is_bookmarked",
        )

    def get_category_label(self, obj):
        return CATEGORY_LABELS.get(obj.category, obj.category)

    def get_city_label(self, obj):
        return CITIES.get(obj.city, obj.city)

    def get_price_display(self, obj):
        if obj.price is None:
            return "По договорённости"
        return f"{format_price(obj.price)} ₽"

    def get_cover_image(self, obj):
        images = ordered_images(obj)
        return absolute_url(images[0]) if images else None

    def get_is_bookmarked(self, obj):
        bookmarked = self.context.get("bookmarked_ids")
        if bookmarked is None:
            return False
        return obj.pk in bookmarked


class ListingDetailSerializer(ListingListSerializer):
    body = serializers.CharField()
    images = serializers.SerializerMethodField()
    condition_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    seller = PublicSellerSerializer(source="user", read_only=True)
    phone_masked = serializers.CharField(read_only=True)
    is_owner = serializers.SerializerMethodField()
    moderation_note = serializers.CharField(read_only=True)
    pending_revision = serializers.JSONField(read_only=True)

    class Meta(ListingListSerializer.Meta):
        fields = ListingListSerializer.Meta.fields + (
            "body",
            "images",
            "cover_index",
            "condition_label",
            "status_label",
            "public_url",
            "seller",
            "phone_masked",
            "is_owner",
            "moderation_note",
            "pending_revision",
            "published_at",
            "ever_published",
        )

    def get_images(self, obj):
        return absolute_urls(ordered_images(obj))

    def get_condition_label(self, obj):
        return CONDITION_LABELS.get(obj.condition, obj.condition)

    def get_status_label(self, obj):
        return POST_STATUS_LABELS.get(obj.status, obj.status)

    def get_public_url(self, obj):
        return absolute_url(post_public_url(obj))

    def get_is_owner(self, obj):
        user = self.context.get("request").user
        return user.is_authenticated and obj.user_id == user.id


class ListingWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)
    condition = serializers.ChoiceField(choices=("used", "new"), required=False)
    price = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    cover_index = serializers.IntegerField(required=False, min_value=0, default=0)
    as_draft = serializers.BooleanField(required=False, default=False)

    def to_service_data(self):
        data = dict(self.validated_data)
        data.pop("as_draft", None)
        return data


class ListingReportSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=list(REPORT_REASONS.keys()))
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
