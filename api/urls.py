from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import LoginView, LogoutView, MeView, ProfileView, RegisterView
from api.views.bookmarks import BookmarkListView, ListingBookmarkView
from api.views.categories import CategoryListView
from api.views.listings import (
    ListingContactView,
    ListingDetailView,
    ListingListCreateView,
    ListingRepublishView,
    ListingSubmitView,
    MyListingListView,
)
from api.views.locations import CityListView

app_name = "api"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("me/profile/", ProfileView.as_view(), name="profile"),
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("cities/", CityListView.as_view(), name="cities"),
    path("listings/", ListingListCreateView.as_view(), name="listing-list"),
    path("me/listings/", MyListingListView.as_view(), name="my-listings"),
    path("me/bookmarks/", BookmarkListView.as_view(), name="bookmarks"),
    path("listings/<uuid:post_id>/", ListingDetailView.as_view(), name="listing-detail"),
    path("listings/<uuid:post_id>/submit/", ListingSubmitView.as_view(), name="listing-submit"),
    path("listings/<uuid:post_id>/republish/", ListingRepublishView.as_view(), name="listing-republish"),
    path("listings/<uuid:post_id>/contact/", ListingContactView.as_view(), name="listing-contact"),
    path("listings/<uuid:post_id>/bookmark/", ListingBookmarkView.as_view(), name="listing-bookmark"),
]
