from django.contrib import admin

from messaging.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "image", "created_at", "read_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("post", "buyer", "seller", "updated_at", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("post__title", "buyer__email", "seller__email")
    raw_id_fields = ("post", "buyer", "seller")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "short_body", "has_image", "created_at", "read_at")
    list_filter = ("created_at", "read_at")
    search_fields = ("body", "sender__email", "conversation__post__title")
    raw_id_fields = ("conversation", "sender")

    @admin.display(description="Текст", boolean=False)
    def short_body(self, obj):
        return obj.body[:80] if obj.body else ("[фото]" if obj.image else "—")

    @admin.display(description="Фото", boolean=True)
    def has_image(self, obj):
        return bool(obj.image)
