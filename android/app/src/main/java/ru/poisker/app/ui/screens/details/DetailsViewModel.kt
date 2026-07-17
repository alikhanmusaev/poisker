package ru.poisker.app.ui.screens.details

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.BookmarkRepository
import ru.poisker.app.data.repository.ListingRepository
import javax.inject.Inject

data class DetailsUiState(
    val listing: ru.poisker.app.data.remote.dto.ListingDto? = null,
    val isLoading: Boolean = true,
    val isContactLoading: Boolean = false,
    val isBookmarkLoading: Boolean = false,
    val error: String? = null,
    val phone: String? = null,
)

@HiltViewModel
class DetailsViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
    private val bookmarkRepository: BookmarkRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DetailsUiState())
    val state = _state.asStateFlow()

    private var loadJob: Job? = null
    private var requestedId: String? = null

    fun load(id: String) {
        requestedId = id
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            _state.value = DetailsUiState(isLoading = true)
            try {
                val listing = listingRepository.listing(id)
                if (requestedId != id) return@launch
                _state.value = DetailsUiState(listing = listing, isLoading = false)
            } catch (e: ApiException) {
                if (requestedId != id) return@launch
                _state.value = DetailsUiState(error = e.message, isLoading = false)
            }
        }
    }

    fun toggleBookmark() {
        val listing = _state.value.listing ?: return
        if (_state.value.isBookmarkLoading) return
        viewModelScope.launch {
            _state.value = _state.value.copy(isBookmarkLoading = true, error = null)
            try {
                if (listing.isBookmarked) bookmarkRepository.remove(listing.id)
                else bookmarkRepository.add(listing.id)
                _state.value = _state.value.copy(
                    listing = listing.copy(isBookmarked = !listing.isBookmarked),
                    isBookmarkLoading = false,
                )
            } catch (e: ApiException) {
                _state.value = _state.value.copy(error = e.message, isBookmarkLoading = false)
            }
        }
    }

    fun revealPhone() {
        val id = _state.value.listing?.id ?: return
        if (_state.value.isContactLoading) return
        viewModelScope.launch {
            _state.value = _state.value.copy(isContactLoading = true, error = null)
            try {
                val response = listingRepository.contact(id)
                _state.value = _state.value.copy(phone = response.phone, isContactLoading = false)
            } catch (e: ApiException) {
                _state.value = _state.value.copy(error = e.message, isContactLoading = false)
            }
        }
    }

    suspend fun isLoggedIn(): Boolean = authRepository.isLoggedIn.first()
}
