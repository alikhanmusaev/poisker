package ru.poisker.app.data.repository

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import ru.poisker.app.data.local.StoredUser
import ru.poisker.app.data.local.TokenStore
import ru.poisker.app.di.MainApi
import ru.poisker.app.data.remote.PoiskerApi
import ru.poisker.app.data.remote.dto.ApiErrorDto
import ru.poisker.app.data.remote.dto.EmailRequestDto
import ru.poisker.app.data.remote.dto.LoginRequestDto
import ru.poisker.app.data.remote.dto.LogoutRequestDto
import ru.poisker.app.data.remote.dto.RegisterRequestDto
import ru.poisker.app.data.remote.dto.SendMessageRequestDto
import ru.poisker.app.data.remote.dto.UserDto
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

class ApiException(
    val code: String?,
    override val message: String,
    val fields: Map<String, List<String>>? = null,
) : Exception(message)

@Singleton
class AuthRepository @Inject constructor(
    @MainApi private val api: PoiskerApi,
    private val tokenStore: TokenStore,
) {
    val currentUser = tokenStore.currentUser
    val isLoggedIn = tokenStore.isLoggedIn

    suspend fun login(email: String, password: String): UserDto {
        return runApi {
            val response = api.login(LoginRequestDto(email.trim().lowercase(), password))
            tokenStore.setSession(
                access = response.tokens.access,
                refresh = response.tokens.refresh,
                user = response.user.toStored(),
            )
            response.user
        }
    }

    suspend fun register(
        displayName: String,
        email: String,
        phone: String,
        password: String,
        acceptTerms: Boolean,
        acceptPdn: Boolean,
    ): UserDto = runApi {
        api.register(
            RegisterRequestDto(
                displayName = displayName.trim(),
                email = email.trim().lowercase(),
                phone = phone.trim(),
                password = password,
                acceptTerms = acceptTerms,
                acceptPdn = acceptPdn,
            ),
        ).user
    }

    suspend fun logout() {
        val refresh = tokenStore.getRefreshToken()
        if (!refresh.isNullOrBlank()) {
            try {
                api.logout(LogoutRequestDto(refresh))
            } catch (_: Exception) {
            }
        }
        tokenStore.clear()
    }

    suspend fun refreshProfile(): UserDto = runApi {
        val user = api.me()
        tokenStore.saveUser(user.toStored())
        user
    }

    suspend fun requestPasswordReset(email: String): String = runApi {
        api.requestPasswordReset(EmailRequestDto(email.trim().lowercase())).message
    }

    suspend fun resendVerification(email: String): String = runApi {
        api.resendVerification(EmailRequestDto(email.trim().lowercase())).message
    }
}

@Singleton
class CatalogRepository @Inject constructor(
    @MainApi private val api: PoiskerApi,
) {
    suspend fun categories() = runApi { api.categories() }
    suspend fun cities(search: String? = null) = runApi { api.cities(search) }
}

@Singleton
class ListingRepository @Inject constructor(
    @MainApi private val api: PoiskerApi,
) {
    suspend fun listings(
        search: String? = null,
        city: String? = null,
        category: String? = null,
        ordering: String? = null,
        page: Int = 1,
    ) = runApi {
        api.listings(search, city, category, ordering, page = page)
    }

    suspend fun listing(id: String) = runApi { api.listing(id) }

    suspend fun myListings(page: Int = 1) = runApi { api.myListings(page) }

    suspend fun createListing(
        title: String,
        body: String,
        category: String,
        city: String,
        condition: String,
        price: Int?,
        imageFiles: List<File>,
        coverIndex: Int = 0,
        asDraft: Boolean = false,
    ) = runApi {
        val text = "text/plain".toMediaType()
        val images = imageFiles.map { file ->
            MultipartBody.Part.createFormData(
                "images",
                file.name,
                file.asRequestBody("image/jpeg".toMediaType()),
            )
        }
        api.createListing(
            title = title.toRequestBody(text),
            body = body.toRequestBody(text),
            category = category.toRequestBody(text),
            city = city.toRequestBody(text),
            condition = condition.toRequestBody(text),
            price = price?.toString()?.toRequestBody(text),
            coverIndex = coverIndex.toString().toRequestBody(text),
            asDraft = asDraft.toString().toRequestBody(text),
            images = images,
        )
    }

    suspend fun updateListing(
        id: String,
        title: String,
        body: String,
        category: String,
        city: String,
        condition: String,
        price: Int?,
        imageFiles: List<File> = emptyList(),
        coverIndex: Int = 0,
        asDraft: Boolean = false,
    ) = runApi {
        val text = "text/plain".toMediaType()
        if (imageFiles.isEmpty()) {
            api.updateListing(
                id,
                mapOf(
                    "title" to title,
                    "body" to body,
                    "category" to category,
                    "city" to city,
                    "condition" to condition,
                    "price" to price,
                    "cover_index" to coverIndex,
                    "as_draft" to asDraft,
                ),
            )
        } else {
            val images = imageFiles.map { file ->
                MultipartBody.Part.createFormData(
                    "images",
                    file.name,
                    file.asRequestBody("image/jpeg".toMediaType()),
                )
            }
            api.updateListingMultipart(
                id = id,
                title = title.toRequestBody(text),
                body = body.toRequestBody(text),
                category = category.toRequestBody(text),
                city = city.toRequestBody(text),
                condition = condition.toRequestBody(text),
                price = price?.toString()?.toRequestBody(text),
                coverIndex = coverIndex.toString().toRequestBody(text),
                asDraft = asDraft.toString().toRequestBody(text),
                images = images,
            )
        }
    }

    suspend fun submitListing(id: String) = runApi { api.submitListing(id) }

    suspend fun republishListing(id: String) = runApi { api.republishListing(id) }

    suspend fun updateListingFields(id: String, fields: Map<String, Any?>) =
        runApi { api.updateListing(id, fields) }

    suspend fun deleteListing(id: String) = runApi { api.deleteListing(id) }

    suspend fun contact(id: String) = runApi { api.contact(id) }
}

@Singleton
class BookmarkRepository @Inject constructor(
    @MainApi private val api: PoiskerApi,
) {
    suspend fun bookmarks(page: Int = 1) = runApi { api.bookmarks(page) }
    suspend fun add(id: String) = runApi { api.addBookmark(id) }
    suspend fun remove(id: String) = runApi { api.removeBookmark(id) }
}

@Singleton
class MessagingRepository @Inject constructor(
    @MainApi private val api: PoiskerApi,
) {
    suspend fun conversations() = runApi { api.conversations() }
    suspend fun unreadCount() = runApi { api.unreadCount() }
    suspend fun conversation(id: String) = runApi { api.conversation(id) }
    suspend fun sendMessage(id: String, body: String) = runApi { api.sendMessage(id, SendMessageRequestDto(body)) }
    suspend fun startConversation(listingId: String, body: String = "") =
        runApi { api.startConversation(listingId, SendMessageRequestDto(body)) }
    suspend fun deleteConversation(id: String) = runApi { api.deleteConversation(id) }
}

private fun UserDto.toStored() = StoredUser(
    id = id,
    email = email,
    displayName = displayName,
    emailVerified = emailVerified,
)

fun ApiException.userMessage(): String {
    fields?.get("non_field_errors")?.firstOrNull()?.let { return it }
    fields?.entries?.firstOrNull()?.let { (field, messages) ->
        val label = FIELD_LABELS[field] ?: field
        val text = messages.firstOrNull() ?: return message
        return if (field in FIELD_LABELS) "$label: $text" else text
    }
    return message
}

private val FIELD_LABELS = mapOf(
    "display_name" to "Имя",
    "email" to "Email",
    "phone" to "Телефон",
    "password" to "Пароль",
    "accept_terms" to "Условия использования",
    "accept_pdn" to "Согласие на обработку данных",
)

suspend fun <T> runApi(block: suspend () -> T): T {
    try {
        return block()
    } catch (e: HttpException) {
        val error = e.response()?.errorBody()?.string()?.let { body ->
            runCatching {
                kotlinx.serialization.json.Json { ignoreUnknownKeys = true }
                    .decodeFromString(ApiErrorDto.serializer(), body)
            }.getOrNull()
        }
        throw ApiException(
            code = error?.code,
            message = error?.message ?: "Ошибка сервера (${e.code()})",
            fields = error?.fields,
        )
    } catch (e: UnknownHostException) {
        throw ApiException(null, "Нет подключения к интернету")
    } catch (e: SocketTimeoutException) {
        throw ApiException(null, "Сервер не отвечает. Проверьте интернет")
    } catch (e: IOException) {
        throw ApiException(null, "Ошибка сети: ${e.message ?: "нет соединения"}")
    } catch (e: kotlinx.serialization.SerializationException) {
        throw ApiException(null, "Ошибка обработки ответа сервера")
    }
}
