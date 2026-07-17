package ru.poisker.app.ui.screens.bookmarks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.ListingCard
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun BookmarksScreen(
    onListingClick: (String) -> Unit,
    viewModel: BookmarksViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    when {
        state.isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        state.error != null -> ErrorBanner(state.error!!)
        else -> LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(PoiskerSpacing.md),
            verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
        ) {
            items(state.listings, key = { it.id }) { listing ->
                ListingCard(listing, onClick = { onListingClick(listing.id) })
            }
        }
    }
}
