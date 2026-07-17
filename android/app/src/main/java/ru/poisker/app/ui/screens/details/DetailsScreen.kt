package ru.poisker.app.ui.screens.details

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailsScreen(
    listingId: String,
    onBack: () -> Unit,
    onLoginRequired: () -> Unit,
    onEdit: (String) -> Unit,
    onMessage: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: DetailsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    LaunchedEffect(listingId) { viewModel.load(listingId) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Объявление") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        LucideIcon(LucideIcons.ArrowLeft, contentDescription = "Назад")
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.isLoading -> Box(
                Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = PoiskerColors.Primary)
            }
            state.error != null && state.listing == null -> ErrorBanner(state.error!!, Modifier.padding(padding))
            state.listing != null -> {
                val listing = state.listing!!
                Column(
                    modifier = modifier
                        .fillMaxSize()
                        .padding(padding)
                        .verticalScroll(rememberScrollState())
                        .padding(PoiskerSpacing.lg),
                    verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
                ) {
                    val images = listing.images.ifEmpty { listOfNotNull(listing.coverImage) }
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
                        items(images) { url ->
                            AsyncImage(
                                model = url,
                                contentDescription = null,
                                modifier = Modifier
                                    .fillMaxWidth(0.92f)
                                    .aspectRatio(4f / 3f),
                                contentScale = ContentScale.Crop,
                            )
                        }
                    }
                    Text(listing.priceDisplay, color = PoiskerColors.PrimaryDark, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text(listing.title, style = MaterialTheme.typography.titleLarge)
                    Text(
                        "${listing.conditionLabel ?: if (listing.condition == "new") "Новый" else "Б/У"} · ${listing.cityLabel} · ${listing.categoryLabel}",
                        color = PoiskerColors.Muted,
                    )
                    listing.seller?.let {
                        Text("Продавец: ${it.displayName} · ★ ${"%.1f".format(it.ratingAvg)}", color = PoiskerColors.Muted)
                    }
                    Text("Просмотров: ${listing.views}")
                    Text(
                        "Будьте осторожны при сделках: не переводите предоплату незнакомым продавцам.",
                        style = MaterialTheme.typography.bodySmall,
                        color = PoiskerColors.WarningText,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = PoiskerSpacing.sm),
                    )
                    Text(listing.body.orEmpty(), style = MaterialTheme.typography.bodyLarge)
                    if (listing.isOwner) {
                        OutlinedButton(onClick = { onEdit(listing.id) }, modifier = Modifier.fillMaxWidth()) {
                            LucideIcon(LucideIcons.Pencil, contentDescription = null)
                            Text("Редактировать")
                        }
                    }
                    listing.moderationNote?.takeIf { it.isNotBlank() }?.let {
                        Text("Модерация: $it", color = PoiskerColors.WarningText)
                    }
                    state.error?.let { ErrorBanner(it) }
                    Row(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
                        Button(onClick = {
                            scope.launch {
                                if (!viewModel.isLoggedIn()) onLoginRequired()
                                else viewModel.revealPhone()
                            }
                        }) {
                            LucideIcon(LucideIcons.Phone, contentDescription = null)
                            Text(state.phone ?: "Показать телефон")
                        }
                        if (!listing.isOwner) {
                            OutlinedButton(onClick = {
                                scope.launch {
                                    if (!viewModel.isLoggedIn()) onLoginRequired()
                                    else onMessage(listing.id)
                                }
                            }) {
                                LucideIcon(LucideIcons.MessagesSquare, contentDescription = null)
                                Text("Написать")
                            }
                        }
                        IconButton(onClick = {
                            scope.launch {
                                if (!viewModel.isLoggedIn()) onLoginRequired()
                                else viewModel.toggleBookmark()
                            }
                        }) {
                            LucideIcon(
                                if (listing.isBookmarked) LucideIcons.BookmarkCheck else LucideIcons.Bookmark,
                                contentDescription = null,
                                tint = PoiskerColors.Primary,
                            )
                        }
                        IconButton(onClick = {
                            val share = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, listing.publicUrl ?: listing.title)
                            }
                            context.startActivity(Intent.createChooser(share, "Поделиться"))
                        }) {
                            LucideIcon(LucideIcons.Share2, contentDescription = null)
                        }
                    }
                    state.phone?.let { phone ->
                        Button(
                            onClick = {
                                context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone")))
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Позвонить $phone")
                        }
                    }
                }
            }
        }
    }
}
