package ru.poisker.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class ApiErrorDto(
    val code: String? = null,
    val message: String? = null,
    val fields: Map<String, List<String>>? = null,
)

@Serializable
data class UserDto(
    val id: Long,
    val email: String,
    @SerialName("display_name") val displayName: String,
    val phone: String,
    @SerialName("email_verified") val emailVerified: Boolean,
    @SerialName("rating_avg") val ratingAvg: Double = 0.0,
    @SerialName("rating_count") val ratingCount: Int = 0,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class TokenPairDto(
    val access: String,
    val refresh: String,
)

@Serializable
data class LoginResponseDto(
    val tokens: TokenPairDto,
    val user: UserDto,
)

@Serializable
data class RegisterResponseDto(
    val user: UserDto,
    val message: String,
)

@Serializable
data class LoginRequestDto(
    val email: String,
    val password: String,
)

@Serializable
data class RegisterRequestDto(
    @SerialName("display_name") val displayName: String,
    val email: String,
    val phone: String,
    val password: String,
    @SerialName("accept_terms") val acceptTerms: Boolean = true,
    @SerialName("accept_pdn") val acceptPdn: Boolean = true,
)

@Serializable
data class RefreshRequestDto(
    val refresh: String,
)

@Serializable
data class RefreshResponseDto(
    val access: String,
    val refresh: String? = null,
)

@Serializable
data class LogoutRequestDto(
    val refresh: String,
)

@Serializable
data class CategoryDto(
    val slug: String,
    val label: String,
    val icon: String,
)

@Serializable
data class CityDto(
    val slug: String,
    val label: String,
)

@Serializable
data class SellerDto(
    val id: Long,
    @SerialName("display_name") val displayName: String,
    @SerialName("rating_avg") val ratingAvg: Double = 0.0,
    @SerialName("rating_count") val ratingCount: Int = 0,
)

@Serializable
data class ListingDto(
    val id: String,
    val title: String,
    val body: String? = null,
    val category: String,
    @SerialName("category_label") val categoryLabel: String,
    val city: String,
    @SerialName("city_label") val cityLabel: String,
    val condition: String,
    @SerialName("condition_label") val conditionLabel: String? = null,
    val price: Int? = null,
    @SerialName("price_display") val priceDisplay: String,
    val status: String,
    @SerialName("status_label") val statusLabel: String? = null,
    @SerialName("has_photo") val hasPhoto: Boolean = false,
    @SerialName("cover_image") val coverImage: String? = null,
    val images: List<String> = emptyList(),
    @SerialName("cover_index") val coverIndex: Int = 0,
    val views: Int = 0,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("published_at") val publishedAt: String? = null,
    @SerialName("ever_published") val everPublished: Boolean = false,
    @SerialName("public_url") val publicUrl: String? = null,
    val seller: SellerDto? = null,
    @SerialName("phone_masked") val phoneMasked: String? = null,
    @SerialName("is_owner") val isOwner: Boolean = false,
    @SerialName("is_bookmarked") val isBookmarked: Boolean = false,
    @SerialName("moderation_note") val moderationNote: String? = null,
    @SerialName("pending_revision") val pendingRevision: JsonElement? = null,
)

@Serializable
data class PaginatedListingsDto(
    val count: Int,
    val next: String? = null,
    val previous: String? = null,
    val results: List<ListingDto>,
)

@Serializable
data class BookmarkDto(
    val id: Long,
    @SerialName("created_at") val createdAt: String,
    val post: ListingDto,
)

@Serializable
data class PaginatedBookmarksDto(
    val count: Int,
    val next: String? = null,
    val previous: String? = null,
    val results: List<BookmarkDto>,
)

@Serializable
data class ContactResponseDto(
    val phone: String,
)

@Serializable
data class BookmarkActionDto(
    val bookmarked: Boolean,
)
