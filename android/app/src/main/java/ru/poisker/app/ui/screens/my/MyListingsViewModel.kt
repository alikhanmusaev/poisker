package ru.poisker.app.ui.screens.my

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.ListingRepository
import javax.inject.Inject

data class MyListingsUiState(
    val listings: List<ListingDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class MyListingsViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MyListingsUiState())
    val state = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = MyListingsUiState(isLoading = true)
            try {
                val response = listingRepository.myListings()
                _state.value = MyListingsUiState(listings = response.results, isLoading = false)
            } catch (e: ApiException) {
                _state.value = MyListingsUiState(error = e.message, isLoading = false)
            }
        }
    }
}
