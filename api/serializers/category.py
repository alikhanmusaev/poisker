from rest_framework import serializers

from listings.constants import CATEGORIES, CATEGORY_ICONS


class CategorySerializer(serializers.Serializer):
    slug = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()


def category_payload():
    return [
        {"slug": slug, "label": label, "icon": CATEGORY_ICONS.get(slug, "layout-grid")}
        for slug, (label, _icon) in CATEGORIES.items()
    ]
