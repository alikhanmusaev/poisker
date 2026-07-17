package ru.poisker.app.ui.screens.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.CategoryDto
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.CatalogRepository
import ru.poisker.app.data.repository.ListingRepository
import java.io.File
import javax.inject.Inject

data class CreateListingUiState(
    val categories: List<CategoryDto> = emptyList(),
    val cities: List<CityDto> = emptyList(),
    val catalogLoaded: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class CreateListingViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
    private val catalogRepository: CatalogRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CreateListingUiState())
    val state = _state.asStateFlow()

    suspend fun ensureAuth(): Boolean = authRepository.isLoggedIn.first()

    fun loadCatalog() {
        viewModelScope.launch {
            try {
                val categories = catalogRepository.categories()
                val cities = catalogRepository.cities()
                _state.update {
                    it.copy(
                        categories = categories,
                        cities = cities,
                        catalogLoaded = categories.isNotEmpty() && cities.isNotEmpty(),
                        error = if (categories.isEmpty() || cities.isEmpty()) {
                            "Не удалось загрузить категории и города"
                        } else {
                            null
                        },
                    )
                }
            } catch (e: ApiException) {
                _state.update { it.copy(catalogLoaded = false, error = e.message) }
            }
        }
    }

    fun searchCities(query: String) {
        viewModelScope.launch {
            try {
                val cities = catalogRepository.cities(query.ifBlank { null })
                _state.update { it.copy(cities = cities) }
            } catch (e: ApiException) {
                _state.update { it.copy(error = e.message) }
            }
        }
    }

    fun create(
        title: String,
        body: String,
        category: String,
        city: String,
        condition: String,
        price: Int?,
        files: List<File>,
        coverIndex: Int,
        onSuccess: (String) -> Unit,
        onAuthRequired: () -> Unit,
    ) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val listing = listingRepository.createListing(
                    title = title,
                    body = body,
                    category = category,
                    city = city,
                    condition = condition,
                    price = price,
                    imageFiles = files,
                    coverIndex = coverIndex,
                )
                _state.update { it.copy(isLoading = false) }
                onSuccess(listing.id)
            } catch (e: ApiException) {
                if (e.code == "authentication_failed") onAuthRequired()
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }
}
