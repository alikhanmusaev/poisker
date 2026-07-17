from django.urls import path, re_path

from core import views

app_name = "core"

urlpatterns = [
    path("suggest", views.suggest_view, name="suggest"),
    path("health", views.health, name="health"),
    path("ready", views.ready, name="ready"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path(
        ".well-known/assetlinks.json",
        views.assetlinks_json,
        name="assetlinks",
    ),
    path("offline", views.offline, name="offline"),
    path("manifest.webmanifest", views.web_manifest, name="web_manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("privacy", views.privacy, name="privacy"),
    path("terms", views.terms, name="terms"),
    path("consent", views.pdn_consent, name="pdn_consent"),
    path("guidelines", views.guidelines, name="guidelines"),
    path(
        "obyavlenie/<slug:city_slug>/<slug:category_slug>/<slug:slug>/<uuid:post_id>/",
        views.post_public,
        name="post_public",
    ),
    path(
        "obyavlenie/<slug:city_slug>/<slug:category_slug>/<slug:slug>/",
        views.post_public_legacy,
        name="post_public_legacy",
    ),
    path("", views.index, name="index"),
    re_path(
        r"^(?P<city_slug>[a-z0-9\-]+)/(?P<category_slug>[a-z0-9\-]+)/$",
        views.city_category_listing,
        name="city_category",
    ),
    re_path(r"^(?P<slug>[a-z0-9\.\-]+)/$", views.slug_router, name="slug_router"),
]
