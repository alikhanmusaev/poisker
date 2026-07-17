package ru.poisker.app.ui.screens.details

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun DetailsScreen(
    listingId: String,
    onBack: () -> Unit,
    onLoginRequired: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: DetailsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    LaunchedEffect(listingId) { viewModel.load(listingId) }

    when {
        state.isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        state.error != null && state.listing == null -> ErrorBanner(state.error!!)
        state.listing != null -> {
            val listing = state.listing!!
            Column(
                modifier = modifier
                    .fillMaxSize()
                    .padding(PoiskerSpacing.lg),
                verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
            ) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
                    val images = listing.images.ifEmpty { listOfNotNull(listing.coverImage) }
                    items(images) { url ->
                        AsyncImage(
                            model = url,
                            contentDescription = null,
                            modifier = Modifier
                                .height(220.dp)
                                .fillMaxWidth(0.85f),
                            contentScale = ContentScale.Crop,
                        )
                    }
                }
                Text(listing.title, style = MaterialTheme.typography.headlineSmall)
                Text(listing.priceDisplay, color = PoiskerColors.Primary, style = MaterialTheme.typography.titleLarge)
                Text("${listing.cityLabel} · ${listing.conditionLabel ?: listing.condition}")
                Text(listing.body.orEmpty(), style = MaterialTheme.typography.bodyLarge)
                listing.seller?.let { Text("Продавец: ${it.displayName}", color = PoiskerColors.Muted) }
                state.error?.let { ErrorBanner(it) }
                Row(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
                    Button(onClick = {
                        scope.launch {
                            if (!viewModel.isLoggedIn()) onLoginRequired()
                            else viewModel.revealPhone()
                        }
                    }) {
                        Icon(Icons.Default.Phone, contentDescription = null)
                        Text(state.phone ?: "Показать телефон")
                    }
                    IconButton(onClick = {
                        scope.launch {
                            if (!viewModel.isLoggedIn()) onLoginRequired()
                            else viewModel.toggleBookmark()
                        }
                    }) {
                        Icon(
                            if (listing.isBookmarked) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
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
                        Icon(Icons.Default.Share, contentDescription = null)
                    }
                }
                Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Назад") }
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
