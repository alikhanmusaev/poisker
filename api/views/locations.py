from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.location import CitySerializer, city_payload


class CityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        search = request.query_params.get("search", "")
        data = CitySerializer(city_payload(search=search), many=True).data
        return Response(data)
