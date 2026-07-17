from rest_framework import serializers

from api.serializers.auth import PublicSellerSerializer
from api.serializers.listing import ListingListSerializer
from api.utils import absolute_url
from messaging.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicSellerSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "body",
            "image_url",
            "created_at",
            "read_at",
            "is_mine",
        )
        read_only_fields = fields

    def get_is_mine(self, obj):
        user = self.context.get("request").user
        return obj.sender_id == user.id

    def get_image_url(self, obj):
        return absolute_url(obj.image) if obj.image else None


class ConversationPostSerializer(ListingListSerializer):
    class Meta(ListingListSerializer.Meta):
        fields = (
            "id",
            "title",
            "category",
            "category_label",
            "city",
            "city_label",
            "price",
            "price_display",
            "cover_image",
            "status",
        )


class ConversationListSerializer(serializers.ModelSerializer):
    post = ConversationPostSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    last_message_body = serializers.SerializerMethodField()
    last_message_image = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    last_message_read_at = serializers.SerializerMethodField()
    last_message_sender_id = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "post",
            "other_user",
            "updated_at",
            "last_message_body",
            "last_message_image",
            "last_message_at",
            "last_message_read_at",
            "last_message_sender_id",
            "unread_count",
        )
        read_only_fields = fields

    def get_other_user(self, obj):
        user = self.context["request"].user
        return PublicSellerSerializer(obj.other_participant(user)).data

    def get_last_message_body(self, obj):
        return getattr(obj, "last_message_body", None) or ""

    def get_last_message_image(self, obj):
        return getattr(obj, "last_message_image", None) or ""

    def get_last_message_at(self, obj):
        return getattr(obj, "last_message_at", None)

    def get_last_message_read_at(self, obj):
        return getattr(obj, "last_message_read_at", None)

    def get_last_message_sender_id(self, obj):
        return getattr(obj, "last_message_sender_id", None)

    def get_unread_count(self, obj):
        return int(getattr(obj, "unread_count", 0) or 0)

class ConversationDetailSerializer(ConversationListSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ("messages",)

    def get_messages(self, obj):
        qs = (
            obj.messages.select_related("sender")
            .exclude(body="", image="")
            .order_by("created_at")
        )
        return MessageSerializer(qs, many=True, context=self.context).data


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")
