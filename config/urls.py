from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from listings.media_views import serve_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("moderation/", include("moderation.urls")),
    path("media/<path:key>", serve_media, name="media"),
    path("accounts/", include("accounts.urls")),
    path("messages/", include("messaging.urls")),
    path("sellers/", include("reviews.urls")),
    path("posts/", include("listings.urls")),
    path("", include("bookmarks.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
