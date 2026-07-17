package ru.poisker.app.ui.screens.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.CategoryDto
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.BookmarkRepository
import ru.poisker.app.data.repository.CatalogRepository
import ru.poisker.app.data.repository.ListingRepository
import javax.inject.Inject

data class HomeUiState(
    val listings: List<ListingDto> = emptyList(),
    val categories: List<CategoryDto> = emptyList(),
    val allCities: List<CityDto> = emptyList(),
    val citySuggestions: List<CityDto> = emptyList(),
    val search: String = "",
    val selectedCity: String? = null,
    val selectedCityLabel: String = "",
    val cityPanelQuery: String = "",
    val isCitySearching: Boolean = false,
    val selectedCategory: String? = null,
    val ordering: String = "date_desc",
    val totalCount: Int = 0,
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
    private val bookmarkRepository: BookmarkRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HomeUiState(isLoading = true))
    val state = _state.asStateFlow()

    private var searchJob: Job? = null
    private var citySearchJob: Job? = null
    private var listingsJob: Job? = null
    private var requestGeneration = 0

    init {
        viewModelScope.launch {
            runCatching {
                val categories = catalogRepository.categories()
                val cities = catalogRepository.cities()
                _state.update { it.copy(categories = categories, allCities = cities) }
            }
            loadListings(reset = true)
        }
    }

    fun onSearchChange(value: String) {
        _state.update { it.copy(search = value) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(400)
            loadListings(reset = true)
        }
    }

    fun onCityPanelQueryChange(query: String) {
        _state.update { it.copy(cityPanelQuery = query) }
        citySearchJob?.cancel()
        if (query.isBlank()) {
            _state.update { it.copy(citySuggestions = emptyList(), isCitySearching = false) }
            return
        }
        citySearchJob = viewModelScope.launch {
            delay(200)
            _state.update { it.copy(isCitySearching = true) }
            runCatching {
                val suggestions = catalogRepository.cities(query)
                _state.update { it.copy(citySuggestions = suggestions, isCitySearching = false) }
            }.onFailure {
                _state.update { it.copy(isCitySearching = false) }
            }
        }
    }

    fun selectCity(slug: String, label: String) {
        _state.update {
            it.copy(
                selectedCity = slug,
                selectedCityLabel = label,
                cityPanelQuery = label,
                citySuggestions = emptyList(),
            )
        }
        loadListings(reset = true)
    }

    fun clearCity() {
        _state.update {
            it.copy(
                selectedCity = null,
                selectedCityLabel = "",
                cityPanelQuery = "",
                citySuggestions = emptyList(),
            )
        }
        loadListings(reset = true)
    }

    fun selectCategory(slug: String?) {
        _state.update { it.copy(selectedCategory = slug) }
        loadListings(reset = true)
    }

    fun selectOrdering(ordering: String) {
        _state.update { it.copy(ordering = ordering) }
        loadListings(reset = true)
    }

    fun clearFilters() {
        _state.update {
            it.copy(
                selectedCity = null,
                selectedCityLabel = "",
                cityPanelQuery = "",
                citySuggestions = emptyList(),
                selectedCategory = null,
                search = "",
                ordering = "date_desc",
            )
        }
        loadListings(reset = true)
    }

    fun refresh() = loadListings(reset = true, refreshing = true)

    fun loadMore() {
        val current = _state.value
        if (current.isLoadingMore || !current.hasMore || current.isLoading) return
        _state.update { it.copy(isLoadingMore = true) }
        loadListings(reset = false)
    }

    fun toggleBookmark(listingId: String, onLoginRequired: () -> Unit) {
        val listing = _state.value.listings.find { it.id == listingId } ?: return
        viewModelScope.launch {
            try {
                if (listing.isBookmarked) bookmarkRepository.remove(listingId)
                else bookmarkRepository.add(listingId)
                _state.update { state ->
                    state.copy(
                        listings = state.listings.map {
                            if (it.id == listingId) it.copy(isBookmarked = !listing.isBookmarked) else it
                        },
                    )
                }
            } catch (e: ApiException) {
                if (e.code == "authentication_failed") onLoginRequired()
                else _state.update { it.copy(error = e.message) }
            }
        }
    }

    private fun loadListings(reset: Boolean, refreshing: Boolean = false) {
        if (reset) {
            listingsJob?.cancel()
            requestGeneration += 1
        } else {
            val current = _state.value
            if (!current.isLoadingMore || !current.hasMore) return
        }

        val generation = requestGeneration
        val snapshot = _state.value
        val page = if (reset) 1 else snapshot.page + 1

        listingsJob = viewModelScope.launch {
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
                    search = snapshot.search.ifBlank { null },
                    city = snapshot.selectedCity,
                    category = snapshot.selectedCategory,
                    ordering = snapshot.ordering,
                    page = page,
                )
                if (generation != requestGeneration) return@launch
                _state.update {
                    val merged = if (reset) response.results else it.listings + response.results
                    it.copy(
                        listings = merged,
                        totalCount = response.count,
                        page = page,
                        hasMore = response.next != null,
                        isLoading = false,
                        isRefreshing = false,
                        isLoadingMore = false,
                    )
                }
            } catch (e: ApiException) {
                if (generation != requestGeneration) return@launch
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
