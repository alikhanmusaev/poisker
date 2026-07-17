package ru.poisker.app.push

import android.content.Context
import android.webkit.CookieManager
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import ru.poisker.app.BuildConfig
import java.util.UUID
import java.util.concurrent.TimeUnit

private val Context.pushDataStore by preferencesDataStore(name = "poisker_push")

class PushTokenManager(private val context: Context) {
    private val deviceIdKey = stringPreferencesKey("device_id")
    private val lastTokenKey = stringPreferencesKey("last_fcm_token")
    private val notifPromptedKey = stringPreferencesKey("notif_permission_prompted")

    private val client = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    suspend fun deviceId(): String {
        val existing = context.pushDataStore.data.map { it[deviceIdKey] }.first()
        if (!existing.isNullOrBlank()) return existing
        val created = UUID.randomUUID().toString()
        context.pushDataStore.edit { it[deviceIdKey] = created }
        return created
    }

    suspend fun saveToken(token: String) {
        context.pushDataStore.edit { it[lastTokenKey] = token }
    }

    suspend fun lastToken(): String? =
        context.pushDataStore.data.map { it[lastTokenKey] }.first()

    suspend fun wasNotificationPrompted(): Boolean =
        context.pushDataStore.data.map { it[notifPromptedKey] == "1" }.first()

    suspend fun markNotificationPrompted() {
        context.pushDataStore.edit { it[notifPromptedKey] = "1" }
    }

    fun isLoggedInViaCookies(): Boolean {
        val cookies = CookieManager.getInstance().getCookie("https://poisker.ru/") ?: return false
        return cookies.split(";").any { it.trim().startsWith("sessionid=") }
    }

    suspend fun registerCurrentToken(token: String? = null): Boolean {
        val fcmToken = token ?: lastToken() ?: return false
        if (!isLoggedInViaCookies()) return false
        saveToken(fcmToken)
        return PushRegistrationClient(client).register(
            token = fcmToken,
            deviceId = deviceId(),
            appVersion = BuildConfig.VERSION_NAME,
            appBuild = BuildConfig.VERSION_CODE,
        )
    }

    suspend fun unregisterCurrentDevice(): Boolean {
        if (!isLoggedInViaCookies()) return false
        return PushRegistrationClient(client).unregister(deviceId())
    }
}

class PushRegistrationClient(
    private val client: OkHttpClient,
) {
    fun register(
        token: String,
        deviceId: String,
        appVersion: String,
        appBuild: Int,
    ): Boolean {
        val cookies = CookieManager.getInstance().getCookie("https://poisker.ru/") ?: return false
        val csrf = extractCookie(cookies, "csrftoken") ?: return false
        val body = JSONObject()
            .put("token", token)
            .put("platform", "android")
            .put("device_id", deviceId)
            .put("app_version", appVersion)
            .put("app_build", appBuild)
            .toString()
            .toRequestBody(JSON_MEDIA)
        val request = Request.Builder()
            .url(BuildConfig.API_BASE_URL + "push/devices/")
            .header("Cookie", cookies)
            .header("X-CSRFToken", csrf)
            .header("Referer", "https://poisker.ru/")
            .header("User-Agent", "PoiskerAndroid/${BuildConfig.VERSION_NAME}")
            .post(body)
            .build()
        return client.newCall(request).execute().use { it.isSuccessful }
    }

    fun unregister(deviceId: String): Boolean {
        val cookies = CookieManager.getInstance().getCookie("https://poisker.ru/") ?: return false
        val csrf = extractCookie(cookies, "csrftoken") ?: return false
        val encoded = java.net.URLEncoder.encode(deviceId, Charsets.UTF_8.name())
        val request = Request.Builder()
            .url(BuildConfig.API_BASE_URL + "push/devices/current/?device_id=$encoded")
            .header("Cookie", cookies)
            .header("X-CSRFToken", csrf)
            .header("X-Device-Id", deviceId)
            .header("Referer", "https://poisker.ru/")
            .header("User-Agent", "PoiskerAndroid/${BuildConfig.VERSION_NAME}")
            .delete()
            .build()
        return client.newCall(request).execute().use { it.isSuccessful }
    }

    private fun extractCookie(cookies: String, name: String): String? =
        cookies.split(";")
            .map { it.trim() }
            .firstOrNull { it.startsWith("$name=") }
            ?.substringAfter("=")

    companion object {
        private val JSON_MEDIA = "application/json; charset=utf-8".toMediaType()
    }
}
