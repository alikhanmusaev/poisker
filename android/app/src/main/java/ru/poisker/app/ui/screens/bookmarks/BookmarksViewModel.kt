package ru.poisker.app.ui.screens.bookmarks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.BookmarkRepository
import javax.inject.Inject

data class BookmarksUiState(
    val listings: List<ListingDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class BookmarksViewModel @Inject constructor(
    private val bookmarkRepository: BookmarkRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(BookmarksUiState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = BookmarksUiState(isLoading = true)
            try {
                val response = bookmarkRepository.bookmarks()
                _state.value = BookmarksUiState(
                    listings = response.results.map { it.post },
                    isLoading = false,
                )
            } catch (e: ApiException) {
                _state.value = BookmarksUiState(error = e.message, isLoading = false)
            }
        }
    }
}
