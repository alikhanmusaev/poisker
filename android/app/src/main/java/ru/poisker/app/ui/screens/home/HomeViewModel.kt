package ru.poisker.app.ui.screens.home

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

data class HomeUiState(
    val listings: List<ListingDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val cities: List<CityDto> = emptyList(),
    val search: String = "",
    val selectedCity: String? = null,
    val selectedCategory: String? = null,
    val ordering: String = "-created_at",
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isLoadingMore: Boolean = false,
    val page: Int = 1,
    val hasMore: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val listingRepository: ListingRepository,
    private val catalogRepository: CatalogRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HomeUiState(isLoading = true))
    val state = _state.asStateFlow()

    init {
        viewModelScope.launch {
            runCatching {
                val categories = catalogRepository.categories()
                val cities = catalogRepository.cities()
                _state.update { it.copy(categories = categories, cities = cities) }
            }
            loadListings(reset = true)
        }
    }

    fun onSearchChange(value: String) {
        _state.update { it.copy(search = value) }
    }

    fun applyFilters(city: String?, category: String?, ordering: String) {
        _state.update {
            it.copy(
                selectedCity = city,
                selectedCategory = category,
                ordering = ordering,
            )
        }
        loadListings(reset = true)
    }

    fun refresh() {
        loadListings(reset = true, refreshing = true)
    }

    fun loadMore() {
        val current = _state.value
        if (current.isLoadingMore || !current.hasMore) return
        loadListings(reset = false)
    }

    private fun loadListings(reset: Boolean, refreshing: Boolean = false) {
        viewModelScope.launch {
            val current = _state.value
            val page = if (reset) 1 else current.page + 1
            _state.update {
                it.copy(
                    isLoading = reset && !refreshing,
                    isRefreshing = refreshing,
                    isLoadingMore = !reset,
                    error = null,
                )
            }
            try {
                val response = listingRepository.listings(
                    search = current.search.ifBlank { null },
                    city = current.selectedCity,
                    category = current.selectedCategory,
                    ordering = current.ordering,
                    page = page,
                )
                _state.update {
                    val merged = if (reset) response.results else it.listings + response.results
                    it.copy(
                        listings = merged,
                        page = page,
                        hasMore = response.next != null,
                        isLoading = false,
                        isRefreshing = false,
                        isLoadingMore = false,
                    )
                }
            } catch (e: ApiException) {
                _state.update {
                    it.copy(
                        error = e.message,
                        isLoading = false,
                        isRefreshing = false,
                        isLoadingMore = false,
                    )
                }
            }
        }
    }
}
