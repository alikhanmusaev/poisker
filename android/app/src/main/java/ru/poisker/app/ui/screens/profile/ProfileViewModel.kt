package ru.poisker.app.ui.screens.profile

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
import ru.poisker.app.data.repository.ListingRepository
import javax.inject.Inject

data class ProfileUiState(
    val isAuthenticated: Boolean = false,
    val displayName: String = "",
    val email: String = "",
    val emailVerified: Boolean = true,
    val tab: String = "active",
    val allListings: List<ListingDto> = emptyList(),
    val listings: List<ListingDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val listingRepository: ListingRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ProfileUiState())
    val state = _state.asStateFlow()

    suspend fun ensureAuth(): Boolean {
        val loggedIn = authRepository.isLoggedIn.first()
        if (loggedIn) {
            _state.update { it.copy(isAuthenticated = true) }
        }
        return loggedIn
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isAuthenticated = true, isLoading = true, error = null) }
            try {
                val user = authRepository.refreshProfile()
                val response = listingRepository.myListings()
                _state.update {
                    it.copy(
                        isAuthenticated = true,
                        displayName = user.displayName,
                        email = user.email,
                        emailVerified = user.emailVerified,
                        allListings = response.results,
                        isLoading = false,
                        isActionLoading = false,
                    )
                }
                applyTab(_state.value.tab)
            } catch (e: ApiException) {
                val authFailed = e.code == "authentication_failed"
                _state.update {
                    it.copy(
                        isLoading = false,
                        isActionLoading = false,
                        error = e.message,
                        isAuthenticated = !authFailed,
                    )
                }
            }
        }
    }

    fun selectTab(tab: String) {
        _state.update { it.copy(tab = tab) }
        applyTab(tab)
    }

    private fun applyTab(tab: String) {
        val filtered = when (tab) {
            "active" -> _state.value.allListings.filter { it.status in setOf("published", "pending") }
            "draft" -> _state.value.allListings.filter { it.status == "draft" }
            "hidden" -> _state.value.allListings.filter { it.status == "hidden" }
            "expired" -> _state.value.allListings.filter { it.status == "expired" }
            else -> _state.value.allListings
        }
        _state.update { it.copy(listings = filtered) }
    }

    fun submit(id: String) = runAction { listingRepository.submitListing(id) }

    fun republish(id: String) = runAction { listingRepository.republishListing(id) }

    fun delete(id: String) = runAction { listingRepository.deleteListing(id) }

    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            authRepository.logout()
            _state.value = ProfileUiState()
            onDone()
        }
    }

    private fun runAction(block: suspend () -> Unit) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, error = null) }
            try {
                block()
                load()
            } catch (e: ApiException) {
                _state.update { it.copy(error = e.message, isActionLoading = false) }
            }
        }
    }
}
