from django.urls import path

from locations import views

app_name = "locations"

urlpatterns = [
    path("search/", views.locations_search, name="search"),
    path("popular/", views.locations_popular, name="popular"),
]
