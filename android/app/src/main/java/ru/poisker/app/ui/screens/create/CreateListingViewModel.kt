package ru.poisker.app.ui.screens.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.ListingRepository
import java.io.File
import javax.inject.Inject

data class CreateListingUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class CreateListingViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CreateListingUiState())
    val state = _state.asStateFlow()

    fun create(
        title: String,
        body: String,
        category: String,
        city: String,
        price: Int?,
        files: List<File>,
        onSuccess: (String) -> Unit,
        onAuthRequired: () -> Unit,
    ) {
        viewModelScope.launch {
            _state.value = CreateListingUiState(isLoading = true)
            try {
                val listing = listingRepository.createListing(
                    title = title,
                    body = body,
                    category = category,
                    city = city,
                    condition = "used",
                    price = price,
                    imageFiles = files,
                )
                _state.value = CreateListingUiState()
                onSuccess(listing.id)
            } catch (e: ApiException) {
                if (e.code == "authentication_failed") onAuthRequired()
                _state.value = CreateListingUiState(error = e.message)
            }
        }
    }
}
