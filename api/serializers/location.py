from rest_framework import serializers

from listings.constants import CITIES
from locations.services.search import popular_settlements, search_settlements


class CitySerializer(serializers.Serializer):
    slug = serializers.CharField()
    label = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    region = serializers.DictField()


def city_payload(search: str = ""):
    settlements = search_settlements(search, limit=20) if search.strip() else popular_settlements(20)
    payload = [
        {
            "id": settlement.id,
            "slug": settlement.slug,
            "label": settlement.name,
            "region": {
                "id": settlement.region_id,
                "slug": settlement.region.slug,
                "name": settlement.region.name,
            },
        }
        for settlement in settlements
    ]
    if payload:
        return payload
    query = search.strip().lower()
    return [
        {"id": None, "slug": slug, "label": label, "region": {}}
        for slug, label in CITIES.items()
        if not query or query in label.lower() or query in slug
    ]
