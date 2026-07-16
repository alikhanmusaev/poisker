from django.urls import path

from reviews import views

app_name = "reviews"

urlpatterns = [
    path("<int:user_id>/", views.seller_profile, name="seller_profile"),
    path("<int:user_id>/review/", views.review_seller, name="review_seller"),
    path(
        "<int:user_id>/reviews/<uuid:review_id>/reply/",
        views.reply_review,
        name="reply_review",
    ),
]
