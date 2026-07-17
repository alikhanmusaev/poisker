package ru.poisker.app.data.remote

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import ru.poisker.app.data.remote.dto.BookmarkActionDto
import ru.poisker.app.data.remote.dto.CategoryDto
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.data.remote.dto.ContactResponseDto
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.remote.dto.LoginRequestDto
import ru.poisker.app.data.remote.dto.LoginResponseDto
import ru.poisker.app.data.remote.dto.LogoutRequestDto
import ru.poisker.app.data.remote.dto.PaginatedBookmarksDto
import ru.poisker.app.data.remote.dto.PaginatedListingsDto
import ru.poisker.app.data.remote.dto.RefreshRequestDto
import ru.poisker.app.data.remote.dto.RefreshResponseDto
import ru.poisker.app.data.remote.dto.RegisterRequestDto
import ru.poisker.app.data.remote.dto.RegisterResponseDto
import ru.poisker.app.data.remote.dto.UserDto

interface PoiskerApi {
    @POST("auth/register/")
    suspend fun register(@Body body: RegisterRequestDto): RegisterResponseDto

    @POST("auth/login/")
    suspend fun login(@Body body: LoginRequestDto): LoginResponseDto

    @POST("auth/refresh/")
    suspend fun refresh(@Body body: RefreshRequestDto): RefreshResponseDto

    @POST("auth/logout/")
    suspend fun logout(@Body body: LogoutRequestDto)

    @GET("auth/me/")
    suspend fun me(): UserDto

    @GET("categories/")
    suspend fun categories(): List<CategoryDto>

    @GET("cities/")
    suspend fun cities(@Query("search") search: String? = null): List<CityDto>

    @GET("listings/")
    suspend fun listings(
        @Query("search") search: String? = null,
        @Query("city") city: String? = null,
        @Query("category") category: String? = null,
        @Query("ordering") ordering: String? = null,
        @Query("min_price") minPrice: Int? = null,
        @Query("max_price") maxPrice: Int? = null,
        @Query("page") page: Int? = null,
    ): PaginatedListingsDto

    @GET("listings/{id}/")
    suspend fun listing(@Path("id") id: String): ListingDto

    @Multipart
    @POST("listings/")
    suspend fun createListing(
        @Part("title") title: RequestBody,
        @Part("body") body: RequestBody,
        @Part("category") category: RequestBody,
        @Part("city") city: RequestBody,
        @Part("condition") condition: RequestBody,
        @Part("price") price: RequestBody?,
        @Part("cover_index") coverIndex: RequestBody?,
        @Part("as_draft") asDraft: RequestBody?,
        @Part images: List<MultipartBody.Part>,
    ): ListingDto

    @PATCH("listings/{id}/")
    suspend fun updateListing(
        @Path("id") id: String,
        @Body body: Map<String, @JvmSuppressWildcards Any?>,
    ): ListingDto

    @DELETE("listings/{id}/")
    suspend fun deleteListing(@Path("id") id: String)

    @GET("me/listings/")
    suspend fun myListings(@Query("page") page: Int? = null): PaginatedListingsDto

    @GET("me/bookmarks/")
    suspend fun bookmarks(@Query("page") page: Int? = null): PaginatedBookmarksDto

    @POST("listings/{id}/bookmark/")
    suspend fun addBookmark(@Path("id") id: String): BookmarkActionDto

    @DELETE("listings/{id}/bookmark/")
    suspend fun removeBookmark(@Path("id") id: String)

    @POST("listings/{id}/contact/")
    suspend fun contact(@Path("id") id: String): ContactResponseDto
}
