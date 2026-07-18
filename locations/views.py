from django.http import JsonResponse
from django.views.decorators.http import require_GET

from locations.services.search import (
    SEARCH_MIN_LEN,
    popular_settlements,
    search_settlements,
    settlement_to_dict,
)


@require_GET
def locations_search(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < SEARCH_MIN_LEN:
        return JsonResponse({"results": [], "message": "Введите минимум 2 символа"})

    region = request.GET.get("region") or ""
    region_id = None
    region_slug = None
    if region.isdigit():
        region_id = int(region)
    elif region:
        region_slug = region

    try:
        limit = int(request.GET.get("limit") or 20)
    except ValueError:
        limit = 20

    rows = search_settlements(
        q, region_id=region_id, region_slug=region_slug, limit=limit
    )
    return JsonResponse({"results": [settlement_to_dict(s) for s in rows]})


@require_GET
def locations_popular(request):
    try:
        limit = int(request.GET.get("limit") or 16)
    except ValueError:
        limit = 16
    rows = popular_settlements(limit=limit)
    return JsonResponse({"results": [settlement_to_dict(s) for s in rows]})
