from django.urls import path

from listings import views
from listings import media_views

app_name = "listings"

urlpatterns = [
    path("new/", views.create, name="create"),
    path("my/", views.my_posts, name="my_posts"),
    path("<uuid:post_id>/contact/", views.contact, name="contact"),
    path("<uuid:post_id>/report/", media_views.report_post, name="report"),
    path("<uuid:post_id>/", views.show, name="show"),
    path("<uuid:post_id>/edit/", views.edit, name="edit"),
    path("<uuid:post_id>/delete/", views.delete, name="delete"),
    path("<uuid:post_id>/republish/", views.republish, name="republish"),
    path("<uuid:post_id>/submit/", views.submit_for_moderation, name="submit"),
]
