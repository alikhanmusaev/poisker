package ru.poisker.app.ui.screens.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.ui.components.EmptyState
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.ListingCard
import ru.poisker.app.ui.components.PoiskerHeader
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

private val TABS = listOf(
    "active" to "Активные",
    "draft" to "Черновики",
    "hidden" to "Скрытые",
    "expired" to "Истёкшие",
)

@Composable
fun ProfileScreen(
    onListingClick: (String) -> Unit,
    onEditListing: (String) -> Unit,
    onLoginRequired: () -> Unit,
    onLoggedOut: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        if (!viewModel.ensureAuth()) onLoginRequired()
        else viewModel.load()
    }

    when {
        !state.isAuthenticated -> Column(modifier.fillMaxSize()) {
            PoiskerHeader()
            EmptyState(
                title = "Войдите в аккаунт",
                hint = "Чтобы видеть профиль и свои объявления",
                actionLabel = "Войти",
                onAction = onLoginRequired,
            )
        }
        state.isLoading && state.listings.isEmpty() -> Column(modifier.fillMaxSize()) {
            PoiskerHeader()
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PoiskerColors.Primary)
            }
        }
        else -> LazyColumn(
            modifier = modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = PoiskerSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
        ) {
            item(key = "header") { PoiskerHeader() }
            item(key = "profile") {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(PoiskerSpacing.lg),
                    verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                ) {
                    Text(
                        state.displayName.ifBlank { "Профиль" },
                        style = MaterialTheme.typography.headlineSmall,
                    )
                    Text(state.email, color = PoiskerColors.Muted)
                    if (!state.emailVerified) {
                        Text(
                            "Подтвердите email для публикации объявлений",
                            color = PoiskerColors.WarningText,
                        )
                    }
                    OutlinedButton(
                        onClick = { viewModel.logout(onLoggedOut) },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("Выйти")
                    }
                }
            }
            item(key = "tabs") {
                LazyRow(
                    contentPadding = PaddingValues(horizontal = PoiskerSpacing.lg),
                    horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                ) {
                    items(TABS.size) { index ->
                        val (key, label) = TABS[index]
                        FilterChip(
                            selected = state.tab == key,
                            onClick = { viewModel.selectTab(key) },
                            label = { Text(label) },
                        )
                    }
                }
            }
            state.error?.let {
                item { ErrorBanner(it, Modifier.padding(horizontal = PoiskerSpacing.lg)) }
            }
            if (state.listings.isEmpty()) {
                item {
                    EmptyState(
                        title = "Нет объявлений",
                        hint = "В этой вкладке пока пусто",
                    )
                }
            } else {
                items(state.listings, key = { it.id }) { listing ->
                    Column(
                        modifier = Modifier.padding(horizontal = PoiskerSpacing.lg),
                        verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                    ) {
                        ListingCard(
                            listing = listing,
                            onClick = { onListingClick(listing.id) },
                            showStatus = true,
                        )
                        ListingOwnerActions(
                            listing = listing,
                            onEdit = { onEditListing(listing.id) },
                            onSubmit = { viewModel.submit(listing.id) },
                            onRepublish = { viewModel.republish(listing.id) },
                            onDelete = { viewModel.delete(listing.id) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ListingOwnerActions(
    listing: ListingDto,
    onEdit: () -> Unit,
    onSubmit: () -> Unit,
    onRepublish: () -> Unit,
    onDelete: () -> Unit,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
        when (listing.status) {
            "draft" -> Button(onClick = onSubmit) { Text("На модерацию") }
            "hidden", "expired" -> Button(onClick = onRepublish) { Text("Опубликовать снова") }
        }
        OutlinedButton(onClick = onEdit) { Text("Изменить") }
        if (listing.status != "deleted") {
            OutlinedButton(onClick = onDelete) { Text("Снять") }
        }
    }
}
