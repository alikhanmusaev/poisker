package ru.poisker.app.ui.screens.home

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.EmptyState
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.HomeSearchBar
import ru.poisker.app.ui.components.InlineLoading
import ru.poisker.app.ui.components.ListingCard
import ru.poisker.app.ui.components.PoiskerHeader
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerIconSizes
import ru.poisker.app.ui.theme.PoiskerSpacing

private val SORT_OPTIONS = listOf(
    "date_desc" to "Сначала новые",
    "price_asc" to "Сначала дешевле",
    "price_desc" to "Сначала дороже",
)

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun HomeScreen(
    onListingClick: (String) -> Unit,
    onLoginRequired: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    var sortMenuExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(listState) {
        snapshotFlow {
            val info = listState.layoutInfo
            val last = info.visibleItemsInfo.lastOrNull()?.index ?: 0
            last >= info.totalItemsCount - 4
        }.collect { nearEnd ->
            if (nearEnd) viewModel.loadMore()
        }
    }

    PullToRefreshBox(
        isRefreshing = state.isRefreshing,
        onRefresh = viewModel::refresh,
        modifier = modifier.fillMaxSize(),
    ) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = PoiskerSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(0.dp),
        ) {
            item(key = "header") {
                PoiskerHeader()
            }
            stickyHeader(key = "search-categories") {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(PoiskerColors.Background)
                        .padding(bottom = PoiskerSpacing.sm),
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = PoiskerSpacing.lg, vertical = PoiskerSpacing.md),
                    ) {
                        HomeSearchBar(
                            search = state.search,
                            onSearchChange = viewModel::onSearchChange,
                            selectedCity = state.selectedCity,
                            selectedCityLabel = state.selectedCityLabel,
                            cityPanelQuery = state.cityPanelQuery,
                            citySuggestions = state.citySuggestions,
                            isCitySearching = state.isCitySearching,
                            onCityPanelQueryChange = viewModel::onCityPanelQueryChange,
                            onCitySelect = viewModel::selectCity,
                            onCityClear = viewModel::clearCity,
                        )
                    }
                    Row(
                        modifier = Modifier
                            .horizontalScroll(rememberScrollState())
                            .padding(horizontal = PoiskerSpacing.lg),
                        horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                    ) {
                        FilterChip(
                            selected = state.selectedCategory == null,
                            onClick = { viewModel.selectCategory(null) },
                            label = { Text("Все") },
                            leadingIcon = {
                                LucideIcon(
                                    LucideIcons.LayoutGrid,
                                    contentDescription = null,
                                    modifier = Modifier.size(PoiskerIconSizes.Inline),
                                )
                            },
                        )
                        state.categories.forEach { category ->
                            FilterChip(
                                selected = state.selectedCategory == category.slug,
                                onClick = { viewModel.selectCategory(category.slug) },
                                label = { Text(category.label) },
                                leadingIcon = {
                                    LucideIcon(
                                        LucideIcons.category(category.icon),
                                        contentDescription = null,
                                        modifier = Modifier.size(PoiskerIconSizes.Inline),
                                    )
                                },
                            )
                        }
                    }
                }
            }
            item(key = "toolbar") {
                Column {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = PoiskerSpacing.lg, vertical = PoiskerSpacing.sm),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = if (state.search.isNotBlank()) {
                                "Найдено: ${state.totalCount}"
                            } else {
                                "${state.totalCount} объявлений"
                            },
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                        )
                        ExposedDropdownMenuBox(
                            expanded = sortMenuExpanded,
                            onExpandedChange = { sortMenuExpanded = it },
                        ) {
                            TextButton(
                                onClick = { sortMenuExpanded = true },
                                modifier = Modifier.menuAnchor(),
                            ) {
                                Text(SORT_OPTIONS.first { it.first == state.ordering }.second)
                            }
                            ExposedDropdownMenu(
                                expanded = sortMenuExpanded,
                                onDismissRequest = { sortMenuExpanded = false },
                            ) {
                                SORT_OPTIONS.forEach { (value, label) ->
                                    DropdownMenuItem(
                                        text = { Text(label) },
                                        onClick = {
                                            viewModel.selectOrdering(value)
                                            sortMenuExpanded = false
                                        },
                                    )
                                }
                            }
                        }
                    }
                    if (state.selectedCity != null || state.selectedCategory != null || state.search.isNotBlank()) {
                        TextButton(
                            onClick = viewModel::clearFilters,
                            modifier = Modifier.padding(horizontal = PoiskerSpacing.lg),
                        ) {
                            Text("Сбросить фильтры", color = PoiskerColors.Primary)
                        }
                    }
                    state.error?.let { ErrorBanner(it) }
                }
            }

            when {
                state.isLoading && state.listings.isEmpty() -> {
                    item(key = "loading") {
                        InlineLoading(size = 40)
                    }
                }
                state.listings.isEmpty() -> {
                    item(key = "empty") {
                        EmptyState(
                            title = "Объявлений нет",
                            hint = "Попробуйте изменить фильтры или поисковый запрос",
                            actionLabel = "Сбросить",
                            onAction = viewModel::clearFilters,
                        )
                    }
                }
                else -> {
                    items(state.listings, key = { it.id }) { listing ->
                        ListingCard(
                            listing = listing,
                            onClick = { onListingClick(listing.id) },
                            onBookmarkClick = {
                                viewModel.toggleBookmark(listing.id, onLoginRequired)
                            },
                            modifier = Modifier.padding(
                                horizontal = PoiskerSpacing.lg,
                                vertical = PoiskerSpacing.sm,
                            ),
                        )
                    }
                    if (state.isLoadingMore) {
                        item(key = "loading-more") {
                            InlineLoading()
                        }
                    }
                }
            }
        }
    }
}
