from messaging.services import unread_messages_count


def messaging_context(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"messages_unread_count": 0}
    return {"messages_unread_count": unread_messages_count(request.user)}
