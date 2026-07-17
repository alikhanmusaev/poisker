package ru.poisker.app.ui.screens.bookmarks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.EmptyState
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.ListingCard
import ru.poisker.app.ui.components.PoiskerHeader
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookmarksScreen(
    onListingClick: (String) -> Unit,
    onLoginRequired: () -> Unit,
    viewModel: BookmarksViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        if (!viewModel.ensureAuth()) onLoginRequired()
        else viewModel.refresh()
    }

    Column(modifier = Modifier.fillMaxSize()) {
        when {
            !state.isAuthenticated -> {
                PoiskerHeader()
                EmptyState(
                    title = "Войдите в аккаунт",
                    hint = "Закладки доступны после входа",
                    actionLabel = "Войти",
                    onAction = onLoginRequired,
                )
            }
            state.isLoading && state.listings.isEmpty() -> {
                PoiskerHeader()
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = PoiskerColors.Primary)
                }
            }
            else -> PullToRefreshBox(
                isRefreshing = state.isRefreshing,
                onRefresh = viewModel::refresh,
                modifier = Modifier.fillMaxSize(),
            ) {
                LazyColumn(
                    contentPadding = PaddingValues(bottom = PoiskerSpacing.lg),
                    verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
                ) {
                    item(key = "header") { PoiskerHeader() }
                    item(key = "title") {
                        Text(
                            "Закладки",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(
                                horizontal = PoiskerSpacing.lg,
                                vertical = PoiskerSpacing.md,
                            ),
                        )
                    }
                    state.error?.let {
                        item { ErrorBanner(it, Modifier.padding(horizontal = PoiskerSpacing.lg)) }
                    }
                    if (state.listings.isEmpty()) {
                        item {
                            EmptyState(
                                title = "Закладок нет",
                                hint = "Сохраняйте объявления с главной или из карточки",
                            )
                        }
                    } else {
                        items(state.listings, key = { it.id }) { listing ->
                            ListingCard(
                                listing = listing.copy(isBookmarked = true),
                                onClick = { onListingClick(listing.id) },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = PoiskerSpacing.lg),
                            )
                        }
                    }
                }
            }
        }
    }
}
