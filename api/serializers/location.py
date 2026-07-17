from rest_framework import serializers

from listings.constants import CITIES


class CitySerializer(serializers.Serializer):
    slug = serializers.CharField()
    label = serializers.CharField()


def city_payload(search: str = ""):
    items = [{"slug": slug, "label": label} for slug, label in CITIES.items()]
    if search:
        q = search.strip().lower()
        items = [item for item in items if q in item["label"].lower() or q in item["slug"]]
    return sorted(items, key=lambda x: x["label"])
