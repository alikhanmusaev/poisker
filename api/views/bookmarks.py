from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.pagination import PoiskerPageNumberPagination
from api.permissions import IsNotBlocked
from api.serializers.bookmark import BookmarkSerializer
from api.serializers.listing import ListingListSerializer
from bookmarks.models import PostBookmark
from listings.models import Post


class BookmarkListView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        qs = (
            PostBookmark.objects.filter(user=request.user)
            .select_related("post", "post__user")
            .order_by("-created_at")
        )
        paginator = PoiskerPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        posts = [b.post for b in page]
        serializer = BookmarkSerializer(
            page,
            many=True,
            context={
                "request": request,
                "bookmarked_ids": {p.pk for p in posts},
            },
        )
        return paginator.get_paginated_response(serializer.data)


class ListingBookmarkView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, status="published")
        bookmark, created = PostBookmark.objects.get_or_create(user=request.user, post=post)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({"bookmarked": True}, status=code)

    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        PostBookmark.objects.filter(user=request.user, post=post).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
