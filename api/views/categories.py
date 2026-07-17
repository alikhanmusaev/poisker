from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.category import CategorySerializer, category_payload


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = CategorySerializer(category_payload(), many=True).data
        return Response(data)
