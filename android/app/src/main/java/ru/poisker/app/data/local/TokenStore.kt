package ru.poisker.app.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import javax.inject.Inject
import javax.inject.Singleton

private val Context.poiskerDataStore by preferencesDataStore("poisker_prefs")

@Singleton
class TokenStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val dataStore = context.poiskerDataStore

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val securePrefs = EncryptedSharedPreferences.create(
        context,
        "poisker_secure_tokens",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    private val _accessToken = MutableStateFlow<String?>(null)
    val accessToken = _accessToken.asStateFlow()

    private val _currentUser = MutableStateFlow<StoredUser?>(null)
    val currentUser = _currentUser.asStateFlow()

    val isLoggedIn: Flow<Boolean> = accessToken.map { !it.isNullOrBlank() }

    init {
        if (!getRefreshToken().isNullOrBlank()) {
            _accessToken.value = runBlocking { dataStore.data.first()[ACCESS_KEY] }
        }
        _currentUser.value = loadUser()
    }

    fun setSession(access: String, refresh: String, user: StoredUser) {
        _accessToken.value = access
        securePrefs.edit().putString(KEY_REFRESH, refresh).apply()
        saveUser(user)
        runBlocking {
            dataStore.edit { prefs -> prefs[ACCESS_KEY] = access }
        }
    }

    fun updateAccess(access: String, refresh: String? = null) {
        _accessToken.value = access
        refresh?.let { securePrefs.edit().putString(KEY_REFRESH, it).apply() }
        runBlocking {
            dataStore.edit { prefs -> prefs[ACCESS_KEY] = access }
        }
    }

    fun getRefreshToken(): String? = securePrefs.getString(KEY_REFRESH, null)

    fun clear() {
        _accessToken.value = null
        _currentUser.value = null
        securePrefs.edit().clear().apply()
        runBlocking { dataStore.edit { it.clear() } }
    }

    fun saveUser(user: StoredUser) {
        _currentUser.value = user
        securePrefs.edit()
            .putLong(KEY_USER_ID, user.id)
            .putString(KEY_USER_EMAIL, user.email)
            .putString(KEY_USER_NAME, user.displayName)
            .putBoolean(KEY_USER_VERIFIED, user.emailVerified)
            .apply()
    }

    private fun loadUser(): StoredUser? {
        val id = securePrefs.getLong(KEY_USER_ID, -1L)
        if (id < 0) return null
        val email = securePrefs.getString(KEY_USER_EMAIL, null) ?: return null
        val name = securePrefs.getString(KEY_USER_NAME, null) ?: return null
        val verified = securePrefs.getBoolean(KEY_USER_VERIFIED, false)
        return StoredUser(id, email, name, verified)
    }

    companion object {
        private const val KEY_REFRESH = "refresh"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_USER_NAME = "user_name"
        private const val KEY_USER_VERIFIED = "user_verified"
        private val ACCESS_KEY = stringPreferencesKey("access_token")
    }
}

data class StoredUser(
    val id: Long,
    val email: String,
    val displayName: String,
    val emailVerified: Boolean,
)
