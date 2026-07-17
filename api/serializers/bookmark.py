from rest_framework import serializers

from api.serializers.listing import ListingListSerializer
from bookmarks.models import PostBookmark


class BookmarkSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(source="post", read_only=True)

    class Meta:
        model = PostBookmark
        fields = ("id", "created_at", "listing")
