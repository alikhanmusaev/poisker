from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from listings.media_views import serve_media
from listings.views import tbank_notify

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/locations/", include("locations.urls")),
    path("api/push/", include("notifications.urls")),
    path("moderation/", include("moderation.urls")),
    path("media/<path:key>", serve_media, name="media"),
    path("accounts/", include("accounts.urls")),
    path("messages/", include("messaging.urls")),
    path("sellers/", include("reviews.urls")),
    path("posts/", include("listings.urls")),
    path("payments/tbank/notify/", tbank_notify, name="tbank_notify"),
    path("", include("bookmarks.urls")),
    path("", include("core.urls")),
]

handler400 = "core.views.bad_request"
handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
