from django.urls import path

from bookmarks import views

app_name = "bookmarks"

urlpatterns = [
    path("bookmarks/", views.index, name="index"),
    path("bookmarks/posts/<uuid:post_id>/toggle/", views.toggle_post, name="toggle_post"),
    path(
        "bookmarks/categories/<slug:category>/toggle/",
        views.toggle_category,
        name="toggle_category",
    ),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read-all/", views.mark_all_read, name="mark_all_read"),
    path("notifications/delete-all/", views.delete_all_notifications_view, name="delete_all"),
    path(
        "notifications/<int:notification_id>/read/",
        views.mark_read,
        name="mark_read",
    ),
    path(
        "notifications/<int:notification_id>/delete/",
        views.delete_notification_view,
        name="delete",
    ),
]
