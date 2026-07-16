from bookmarks.services import unread_notifications_count


def bookmarks_context(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"notifications_unread_count": 0}
    return {"notifications_unread_count": unread_notifications_count(request.user)}
