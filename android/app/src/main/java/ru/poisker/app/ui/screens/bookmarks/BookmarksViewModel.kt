package ru.poisker.app.ui.screens.bookmarks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.BookmarkRepository
import javax.inject.Inject

data class BookmarksUiState(
    val isAuthenticated: Boolean = false,
    val listings: List<ListingDto> = emptyList(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class BookmarksViewModel @Inject constructor(
    private val bookmarkRepository: BookmarkRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(BookmarksUiState())
    val state = _state.asStateFlow()

    suspend fun ensureAuth(): Boolean {
        val loggedIn = authRepository.isLoggedIn.first()
        _state.update { it.copy(isAuthenticated = loggedIn) }
        return loggedIn
    }

    fun refresh() {
        viewModelScope.launch {
            if (!authRepository.isLoggedIn.first()) {
                _state.update { it.copy(isAuthenticated = false, isLoading = false) }
                return@launch
            }
            _state.update { it.copy(isRefreshing = true, error = null, isAuthenticated = true) }
            try {
                val response = bookmarkRepository.bookmarks()
                _state.update {
                    it.copy(
                        listings = response.results.map { bookmark -> bookmark.listing },
                        isLoading = false,
                        isRefreshing = false,
                    )
                }
            } catch (e: ApiException) {
                val authFailed = e.code == "authentication_failed"
                _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message,
                        isAuthenticated = !authFailed,
                    )
                }
            }
        }
    }
}
