package ru.poisker.app.data.remote

import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import ru.poisker.app.data.local.TokenStore
import ru.poisker.app.data.remote.dto.RefreshRequestDto
import ru.poisker.app.di.RefreshApi
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenStore: TokenStore,
    @RefreshApi private val refreshApi: PoiskerApi,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val access = tokenStore.accessToken.value
        val authed = if (!access.isNullOrBlank()) {
            original.newBuilder().header("Authorization", "Bearer $access").build()
        } else {
            original
        }

        val response = chain.proceed(authed)
        if (response.code != 401 || access.isNullOrBlank() || original.url.encodedPath.contains("auth/")) {
            return response
        }

        response.close()
        val refresh = tokenStore.getRefreshToken() ?: return response
        return runBlocking {
            try {
                val tokens = refreshApi.refresh(RefreshRequestDto(refresh))
                tokenStore.updateAccess(tokens.access, tokens.refresh)
                chain.proceed(
                    original.newBuilder()
                        .header("Authorization", "Bearer ${tokens.access}")
                        .build(),
                )
            } catch (_: Exception) {
                tokenStore.clear()
                response
            }
        }
    }
}
