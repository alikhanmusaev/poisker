from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.seller_stats import annotate_seller_posts
from api.exceptions import ServiceValidationError
from api.images import resolve_image_updates, upload_files
from api.pagination import PoiskerPageNumberPagination
from api.permissions import IsNotBlocked, IsOwnerOrReadOnly
from api.serializers.listing import ListingDetailSerializer, ListingListSerializer, ListingWriteSerializer
from api.utils import parse_int_param, service_error
from bookmarks.services import bookmarked_post_ids_for, is_post_bookmarked
from listings.constants import ALLOWED_SORTS, DEFAULT_SEARCH_SORT, DEFAULT_SORT
from listings.models import Post
from listings.services.posts import (
    ValidationError as PostValidationError,
    create_post,
    delete_post,
    republish_post,
    submit_draft,
    unpublish_post,
    update_post,
)
from listings.services.search import search_posts
from listings.services.show_context import increment_views
from listings.services.smart_query import parse_search_query


def _parse_remove_indices(request):
    raw = request.data.getlist("remove_images") if hasattr(request.data, "getlist") else []
    if not raw:
        single = request.data.get("remove_images")
        if single is not None:
            raw = [single] if not isinstance(single, list) else single
    return {int(x) for x in raw if str(x).isdigit()}


def _listing_list_context(request, posts):
    ids = [p.pk for p in posts]
    bookmarked = bookmarked_post_ids_for(request.user, ids) if request.user.is_authenticated else set()
    return {"request": request, "bookmarked_ids": bookmarked}


def _can_view_post(user, post: Post) -> bool:
    if post.status == "published" and post.expires_at and post.expires_at > timezone.now():
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return post.user_id == user.id


def _merge_listing_data(post: Post, validated_data: dict) -> dict:
    merged = {
        "title": post.title,
        "body": post.body,
        "category": post.category,
        "city": post.city,
        "condition": post.condition,
        "price": post.price,
        "cover_index": post.cover_index or 0,
    }
    merged.update(validated_data)
    return merged


class ListingListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsNotBlocked()]
        return [AllowAny()]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        parsed = parse_search_query(search)
        city = request.query_params.get("city") or parsed.get("city") or ""
        category = request.query_params.get("category") or parsed.get("category") or ""
        ordering = request.query_params.get("ordering", "")
        if ordering not in ALLOWED_SORTS:
            ordering = DEFAULT_SEARCH_SORT if search else DEFAULT_SORT

        price_min = parse_int_param(
            request.query_params.get("min_price") or parsed.get("price_min"),
            field="min_price",
        )
        price_max = parse_int_param(
            request.query_params.get("max_price") or parsed.get("price_max"),
            field="max_price",
        )

        paginator = PoiskerPageNumberPagination()
        page_size = paginator.get_page_size(request)
        page_number = int(request.query_params.get("page", 1))
        offset = (page_number - 1) * page_size

        search_text = parsed.get("text") or search
        results, total = search_posts(
            query=search_text,
            city=city or None,
            category=category or None,
            price_min=price_min,
            price_max=price_max,
            sort=ordering,
            limit=page_size,
            offset=offset,
            expanded_terms=parsed.get("expanded_terms"),
        )
        posts = [item["post"] for item in results]
        serializer = ListingListSerializer(
            posts,
            many=True,
            context=_listing_list_context(request, posts),
        )
        return Response(
            {
                "count": total,
                "next": self._page_url(request, page_number + 1) if offset + page_size < total else None,
                "previous": self._page_url(request, page_number - 1) if page_number > 1 else None,
                "results": serializer.data,
            }
        )

    def _page_url(self, request, page):
        if page < 1:
            return None
        params = request.query_params.copy()
        params["page"] = str(page)
        return request.build_absolute_uri(f"{request.path}?{params.urlencode()}")

    def post(self, request):
        write = ListingWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        as_draft = write.validated_data.pop("as_draft", False)
        cover_index = write.validated_data.get("cover_index", 0)
        files = request.FILES.getlist("images")
        image_keys = upload_files(files) if files else []
        if image_keys:
            cover_index = max(0, min(cover_index, len(image_keys) - 1))

        try:
            post = create_post(
                request.user,
                {**write.to_service_data(), "cover_index": cover_index},
                image_keys=image_keys,
                as_draft=as_draft,
            )
        except PostValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc

        return Response(
            ListingDetailSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyListingListView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        qs = annotate_seller_posts(
            Post.objects.filter(user=request.user).exclude(status="deleted")
        ).select_related("user").order_by("-created_at")

        paginator = PoiskerPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        posts = list(page)
        serializer = ListingListSerializer(
            posts,
            many=True,
            context=_listing_list_context(request, posts),
        )
        return paginator.get_paginated_response(serializer.data)


class ListingDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsNotBlocked(), IsOwnerOrReadOnly()]

    def get_object(self, post_id):
        return get_object_or_404(Post.objects.select_related("user"), pk=post_id)

    def get(self, request, post_id):
        post = self.get_object(post_id)
        if not _can_view_post(request.user, post):
            return Response(
                {"code": "not_found", "message": "Не найдено"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if post.status == "published":
            increment_views(request, post)
        bookmarked = {post.pk} if is_post_bookmarked(request.user, post) else set()
        return Response(
            ListingDetailSerializer(
                post,
                context={"request": request, "bookmarked_ids": bookmarked},
            ).data
        )

    def patch(self, request, post_id):
        post = self.get_object(post_id)
        if post.user_id != request.user.id:
            return Response(
                {"code": "permission_denied", "message": "Недостаточно прав"},
                status=status.HTTP_403_FORBIDDEN,
            )

        write = ListingWriteSerializer(data=request.data, partial=True)
        write.is_valid(raise_exception=True)
        as_draft = write.validated_data.pop("as_draft", False)
        cover_index = int(request.data.get("cover_index", post.cover_index or 0))

        remove_idx = _parse_remove_indices(request)
        new_files = request.FILES.getlist("images")
        resolved = resolve_image_updates(
            list(post.images or []),
            remove_idx,
            new_files,
            cover_index,
            post.cover_index or 0,
        )
        image_keys = resolved[0] if resolved else None
        if resolved:
            cover_index = resolved[1]

        try:
            post = update_post(
                post,
                request.user,
                _merge_listing_data(post, {**write.to_service_data(), "cover_index": cover_index}),
                as_draft=as_draft,
                image_keys=image_keys,
            )
        except PostValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc

        return Response(ListingDetailSerializer(post, context={"request": request}).data)

    def delete(self, request, post_id):
        post = self.get_object(post_id)
        if post.user_id != request.user.id:
            return Response(
                {"code": "permission_denied", "message": "Недостаточно прав"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            if post.status == "published":
                unpublish_post(post, request.user)
                post.refresh_from_db()
                return Response(ListingDetailSerializer(post, context={"request": request}).data)
            delete_post(post, request.user)
        except PostValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, user=request.user)
        try:
            post = submit_draft(post, request.user)
        except PostValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc
        return Response(ListingDetailSerializer(post, context={"request": request}).data)


class ListingRepublishView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, user=request.user)
        try:
            post = republish_post(post, request.user)
        except PostValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc
        return Response(ListingDetailSerializer(post, context={"request": request}).data)


class ListingContactView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, post_id):
        from django.conf import settings

        from core.ratelimit import hit_rate_limit

        limit = getattr(settings, "CONTACT_RATE_LIMIT_PER_HOUR", 30)
        if hit_rate_limit(
            f"contact-rate:{request.user.id}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            return Response(
                {"code": "rate_limited", "message": "Слишком много запросов. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        post = get_object_or_404(
            Post.objects.select_related("user"),
            pk=post_id,
            status="published",
        )
        if post.expires_at and post.expires_at <= timezone.now():
            return Response(
                {"code": "not_found", "message": "Не найдено"},
                status=status.HTTP_404_NOT_FOUND,
            )

        phone = post.contact_phone or post.user.phone or ""
        if not phone:
            return Response(
                {"code": "not_found", "message": "Телефон не указан"},
                status=status.HTTP_404_NOT_FOUND,
            )

        Post.objects.filter(pk=post.pk).update(contact_clicks=F("contact_clicks") + 1)
        if request.user.id != post.user_id:
            from reviews.services import record_phone_reveal

            record_phone_reveal(reviewer=request.user, post=post)
        return Response({"phone": phone})
