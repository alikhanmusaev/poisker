package ru.poisker.app.ui.screens.edit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.CategoryDto
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.CatalogRepository
import ru.poisker.app.data.repository.ListingRepository
import javax.inject.Inject

data class EditListingUiState(
    val listing: ListingDto? = null,
    val categories: List<CategoryDto> = emptyList(),
    val cities: List<CityDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class EditListingViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
    private val catalogRepository: CatalogRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(EditListingUiState())
    val state = _state.asStateFlow()

    fun load(id: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val listing = listingRepository.listing(id)
                val categories = catalogRepository.categories()
                val cities = catalogRepository.cities()
                _state.update {
                    it.copy(listing = listing, categories = categories, cities = cities, isLoading = false)
                }
            } catch (e: ApiException) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun searchCities(query: String) {
        viewModelScope.launch {
            runCatching {
                val cities = catalogRepository.cities(query.ifBlank { null })
                _state.update { it.copy(cities = cities) }
            }
        }
    }

    fun save(
        id: String,
        title: String,
        body: String,
        category: String,
        city: String,
        condition: String,
        price: Int?,
        onSaved: () -> Unit,
    ) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                listingRepository.updateListing(
                    id = id,
                    title = title,
                    body = body,
                    category = category,
                    city = city,
                    condition = condition,
                    price = price,
                )
                _state.update { it.copy(isLoading = false) }
                onSaved()
            } catch (e: ApiException) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }
}
