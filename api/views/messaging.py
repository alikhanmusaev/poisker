from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import IsNotBlocked
from api.serializers.messaging import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    SendMessageSerializer,
)
from core.ratelimit import hit_rate_limit
from listings.models import Post
from messaging.services import (
    MessagingError,
    confirm_deal_completed,
    ensure_can_message_post,
    get_conversation_for_user,
    get_or_create_conversation,
    hide_conversation,
    inbox_conversations,
    mark_conversation_read,
    send_message,
    unread_messages_count,
)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        conversations = inbox_conversations(request.user)
        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={"request": request},
        )
        return Response({"count": len(serializer.data), "results": serializer.data})


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request):
        return Response({"count": unread_messages_count(request.user)})


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get(self, request, conversation_id):
        try:
            conversation = get_conversation_for_user(request.user, conversation_id)
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        mark_conversation_read(conversation, request.user)
        serializer = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(serializer.data)

    def delete(self, request, conversation_id):
        try:
            conversation = get_conversation_for_user(request.user, conversation_id)
            hide_conversation(conversation, request.user)
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationMessageCreateView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, conversation_id):
        try:
            conversation = get_conversation_for_user(request.user, conversation_id)
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        limit = getattr(settings, "MESSAGING_RATE_LIMIT_PER_HOUR", 60)
        if hit_rate_limit(
            f"msg-rate:{request.user.id}",
            limit=limit,
            window_seconds=3600,
            fail_closed=True,
        ):
            return Response(
                {"message": "Слишком много сообщений. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            message = send_message(conversation, request.user, serializer.validated_data.get("body", ""))
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from api.serializers.messaging import MessageSerializer

        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ListingConversationStartView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, post_id):
        post = get_object_or_404(Post.objects.select_related("user"), pk=post_id)

        try:
            ensure_can_message_post(post, request.user)
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body = serializer.validated_data.get("body", "")

        conversation = get_or_create_conversation(post, request.user)

        if body.strip():
            limit = getattr(settings, "MESSAGING_RATE_LIMIT_PER_HOUR", 60)
            if hit_rate_limit(
                f"msg-rate:{request.user.id}",
                limit=limit,
                window_seconds=3600,
                fail_closed=True,
            ):
                return Response(
                    {"message": "Слишком много сообщений. Попробуйте позже."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            try:
                send_message(conversation, request.user, body)
            except MessagingError as exc:
                return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        mark_conversation_read(conversation, request.user)
        detail = ConversationDetailSerializer(conversation, context={"request": request})
        return Response(detail.data, status=status.HTTP_201_CREATED)


class ConversationConfirmDealView(APIView):
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def post(self, request, conversation_id):
        try:
            conversation = get_conversation_for_user(request.user, conversation_id)
            conversation = confirm_deal_completed(conversation, request.user)
        except MessagingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        mark_conversation_read(conversation, request.user)
        return Response(
            ConversationDetailSerializer(conversation, context={"request": request}).data
        )
