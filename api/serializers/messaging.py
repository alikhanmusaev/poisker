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
    deal_confirmed_by_me = serializers.SerializerMethodField()
    deal_confirmed_by_other = serializers.SerializerMethodField()
    both_deal_confirmed = serializers.SerializerMethodField()
    can_confirm_deal = serializers.SerializerMethodField()
    can_review_seller = serializers.SerializerMethodField()
    has_existing_review = serializers.SerializerMethodField()
    review_unlock_at = serializers.SerializerMethodField()
    review_via_timeout = serializers.SerializerMethodField()
    other_user_id = serializers.SerializerMethodField()

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + (
            "messages",
            "deal_confirmed_by_me",
            "deal_confirmed_by_other",
            "both_deal_confirmed",
            "can_confirm_deal",
            "can_review_seller",
            "has_existing_review",
            "review_unlock_at",
            "review_via_timeout",
            "other_user_id",
        )

    def get_messages(self, obj):
        qs = (
            obj.messages.select_related("sender")
            .exclude(body="", image="")
            .order_by("created_at")
        )
        return MessageSerializer(qs, many=True, context=self.context).data

    def _other(self, obj):
        user = self.context["request"].user
        return obj.other_participant(user)

    def get_other_user_id(self, obj):
        other = self._other(obj)
        return other.id if other else None

    def get_deal_confirmed_by_me(self, obj):
        return obj.deal_confirmed_by(self.context["request"].user)

    def get_deal_confirmed_by_other(self, obj):
        other = self._other(obj)
        return obj.deal_confirmed_by(other) if other else False

    def get_both_deal_confirmed(self, obj):
        return obj.both_deal_confirmed

    def get_can_confirm_deal(self, obj):
        user = self.context["request"].user
        has_messages = obj.messages.exclude(body="", image="").exists()
        return has_messages and not obj.deal_confirmed_by(user)

    def get_can_review_seller(self, obj):
        user = self.context["request"].user
        if user.id != obj.buyer_id:
            return False
        from reviews.services import can_review_seller

        return can_review_seller(user, self._other(obj))

    def get_has_existing_review(self, obj):
        user = self.context["request"].user
        if user.id != obj.buyer_id:
            return False
        from reviews.services import get_review

        return get_review(user, self._other(obj)) is not None

    def get_review_unlock_at(self, obj):
        user = self.context["request"].user
        if user.id != obj.buyer_id:
            return None
        from reviews.services import conversation_review_unlock_at

        unlock = conversation_review_unlock_at(obj)
        return unlock.isoformat() if unlock else None

    def get_review_via_timeout(self, obj):
        user = self.context["request"].user
        if user.id != obj.buyer_id:
            return False
        from reviews.services import conversation_review_via_timeout

        return conversation_review_via_timeout(obj)


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="")
