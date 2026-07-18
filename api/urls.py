from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from api.views.auth import (
    LoginView,
    LogoutView,
    MeView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    ResendVerificationView,
)
from api.views.bookmarks import BookmarkListView, ListingBookmarkView
from api.views.categories import CategoryListView
from api.views.listings import (
    ListingContactView,
    ListingDetailView,
    ListingListCreateView,
    ListingRepublishView,
    ListingReportView,
    ListingSubmitView,
    MyListingListView,
)
from api.views.locations import CityListView
from api.views.messaging import (
    ConversationConfirmDealView,
    ConversationDetailView,
    ConversationListView,
    ConversationMessageCreateView,
    ListingConversationStartView,
    UnreadCountView,
)

app_name = "api"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("me/profile/", ProfileView.as_view(), name="profile"),
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("cities/", CityListView.as_view(), name="cities"),
    path("listings/", ListingListCreateView.as_view(), name="listing-list"),
    path("me/listings/", MyListingListView.as_view(), name="my-listings"),
    path("me/bookmarks/", BookmarkListView.as_view(), name="bookmarks"),
    path("me/conversations/", ConversationListView.as_view(), name="conversations"),
    path("me/conversations/unread-count/", UnreadCountView.as_view(), name="conversations-unread"),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        ConversationMessageCreateView.as_view(),
        name="conversation-messages",
    ),
    path(
        "listings/<uuid:post_id>/conversations/",
        ListingConversationStartView.as_view(),
        name="listing-conversation-start",
    ),
    path("listings/<uuid:post_id>/", ListingDetailView.as_view(), name="listing-detail"),
    path("listings/<uuid:post_id>/submit/", ListingSubmitView.as_view(), name="listing-submit"),
    path("listings/<uuid:post_id>/republish/", ListingRepublishView.as_view(), name="listing-republish"),
    path("listings/<uuid:post_id>/contact/", ListingContactView.as_view(), name="listing-contact"),
    path("listings/<uuid:post_id>/bookmark/", ListingBookmarkView.as_view(), name="listing-bookmark"),
    path("listings/<uuid:post_id>/report/", ListingReportView.as_view(), name="listing-report"),
    path(
        "conversations/<uuid:conversation_id>/confirm-deal/",
        ConversationConfirmDealView.as_view(),
        name="conversation-confirm-deal",
    ),
    path("push/", include("notifications.urls")),
]
