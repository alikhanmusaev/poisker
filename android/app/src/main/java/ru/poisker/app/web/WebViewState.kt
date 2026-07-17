package ru.poisker.app.web

import android.os.Bundle

data class WebViewUiState(
    val isLoading: Boolean = true,
    val progress: Int = 0,
    val canGoBack: Boolean = false,
    val currentUrl: String = "",
    val pageError: PageError? = null,
    val isOfflineBeforeLoad: Boolean = false,
    val showOfflineBanner: Boolean = false,
    val isRefreshing: Boolean = false,
)

sealed class PageError {
    data class Network(val description: String) : PageError()
    data class Http(val code: Int) : PageError()
    data class Ssl(val description: String) : PageError()
    data class Unknown(val description: String) : PageError()
}

class WebViewStateHolder {
    var savedState: Bundle? = null
        private set
    var lastLoadedUrl: String? = null

    fun save(bundle: Bundle?) {
        savedState = bundle
    }

    fun consumeSavedState(): Bundle? {
        val state = savedState
        savedState = null
        return state
    }
}
