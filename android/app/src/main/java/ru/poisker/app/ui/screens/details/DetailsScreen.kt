package ru.poisker.app.ui.screens.details

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.FullScreenLoading
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerIconSizes
import ru.poisker.app.ui.theme.PoiskerRadius
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
        containerColor = PoiskerColors.Background,
        topBar = {
            TopAppBar(
                title = { Text("Объявление") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        LucideIcon(LucideIcons.ArrowLeft, contentDescription = "Назад")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = PoiskerColors.Surface,
                    titleContentColor = PoiskerColors.Text,
                    navigationIconContentColor = PoiskerColors.Text,
                ),
            )
        },
    ) { padding ->
        when {
            state.isLoading -> Box(
                Modifier
                    .fillMaxSize()
                    .padding(padding),
            ) {
                FullScreenLoading()
            }
            state.error != null && state.listing == null -> ErrorBanner(
                state.error!!,
                Modifier.padding(padding).padding(PoiskerSpacing.lg),
            )
            state.listing != null -> {
                val listing = state.listing!!
                Column(
                    modifier = modifier
                        .fillMaxSize()
                        .padding(padding)
                        .verticalScroll(rememberScrollState()),
                ) {
                    ListingGallery(listing)

                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(PoiskerSpacing.lg),
                        shape = RoundedCornerShape(PoiskerRadius.lg),
                        color = PoiskerColors.Surface,
                        shadowElevation = 1.dp,
                    ) {
                        Column(
                            modifier = Modifier.padding(PoiskerSpacing.lg),
                            verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
                        ) {
                            Text(
                                listing.priceDisplay,
                                color = PoiskerColors.PrimaryDark,
                                style = MaterialTheme.typography.headlineSmall,
                                fontWeight = FontWeight.Bold,
                            )
                            Text(
                                listing.title,
                                style = MaterialTheme.typography.titleLarge,
                                color = PoiskerColors.Text,
                            )
                            Text(
                                buildString {
                                    append(
                                        listing.conditionLabel
                                            ?: if (listing.condition == "new") "Новый" else "Б/У",
                                    )
                                    append(" · ")
                                    append(listing.cityLabel)
                                    append(" · ")
                                    append(listing.categoryLabel)
                                    append(" · ")
                                    append("${listing.views} просм.")
                                },
                                style = MaterialTheme.typography.bodyMedium,
                                color = PoiskerColors.Muted,
                            )
                            listing.seller?.let { seller ->
                                Text(
                                    buildString {
                                        append("Продавец: ${seller.displayName}")
                                        if (seller.ratingCount > 0) {
                                            append(" · ★ ${"%.1f".format(seller.ratingAvg)}")
                                        }
                                    },
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = PoiskerColors.Muted,
                                )
                            }

                            SafetyNote()

                            if (listing.body.orEmpty().isNotBlank()) {
                                Text(
                                    listing.body.orEmpty(),
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = PoiskerColors.Text,
                                    lineHeight = 24.sp,
                                )
                            }

                            listing.moderationNote?.takeIf { it.isNotBlank() }?.let {
                                Text(
                                    "Модерация: $it",
                                    color = PoiskerColors.WarningText,
                                    style = MaterialTheme.typography.bodyMedium,
                                )
                            }
                            state.error?.let { ErrorBanner(it) }

                            Column(verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
                                if (listing.isOwner) {
                                    OutlinedButton(
                                        onClick = { onEdit(listing.id) },
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(PoiskerRadius.md),
                                    ) {
                                        LucideIcon(LucideIcons.Pencil, contentDescription = null, modifier = Modifier.size(PoiskerIconSizes.Inline))
                                        Spacer(Modifier.width(8.dp))
                                        Text("Редактировать")
                                    }
                                } else {
                                    Button(
                                        onClick = {
                                            scope.launch {
                                                if (!viewModel.isLoggedIn()) onLoginRequired()
                                                else onMessage(listing.id)
                                            }
                                        },
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(PoiskerRadius.md),
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = PoiskerColors.Primary,
                                            contentColor = PoiskerColors.Surface,
                                        ),
                                    ) {
                                        LucideIcon(
                                            LucideIcons.MessagesSquare,
                                            contentDescription = null,
                                            modifier = Modifier.size(PoiskerIconSizes.Inline),
                                            tint = PoiskerColors.Surface,
                                        )
                                        Spacer(Modifier.width(8.dp))
                                        Text("Написать продавцу")
                                    }
                                }

                                OutlinedButton(
                                    onClick = {
                                        scope.launch {
                                            if (!viewModel.isLoggedIn()) onLoginRequired()
                                            else viewModel.revealPhone()
                                        }
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !state.isContactLoading,
                                    shape = RoundedCornerShape(PoiskerRadius.md),
                                ) {
                                    if (state.isContactLoading) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(PoiskerIconSizes.Inline),
                                            color = PoiskerColors.Primary,
                                            strokeWidth = 2.dp,
                                        )
                                        Spacer(Modifier.width(8.dp))
                                        Text("Загрузка…")
                                    } else {
                                        LucideIcon(LucideIcons.Phone, contentDescription = null, modifier = Modifier.size(PoiskerIconSizes.Inline))
                                        Spacer(Modifier.width(8.dp))
                                        Text(state.phone ?: "Показать телефон")
                                    }
                                }

                                state.phone?.let { phone ->
                                    Button(
                                        onClick = {
                                            context.startActivity(
                                                Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone")),
                                            )
                                        },
                                        modifier = Modifier.fillMaxWidth(),
                                        shape = RoundedCornerShape(PoiskerRadius.md),
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = PoiskerColors.PrimaryDark,
                                            contentColor = PoiskerColors.Surface,
                                        ),
                                    ) {
                                        Text("Позвонить $phone")
                                    }
                                }

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                                ) {
                                    OutlinedButton(
                                        onClick = {
                                            scope.launch {
                                                if (!viewModel.isLoggedIn()) onLoginRequired()
                                                else viewModel.toggleBookmark()
                                            }
                                        },
                                        modifier = Modifier.weight(1f),
                                        enabled = !state.isBookmarkLoading,
                                        shape = RoundedCornerShape(PoiskerRadius.md),
                                    ) {
                                        if (state.isBookmarkLoading) {
                                            CircularProgressIndicator(
                                                modifier = Modifier.size(PoiskerIconSizes.Inline),
                                                color = PoiskerColors.Primary,
                                                strokeWidth = 2.dp,
                                            )
                                        } else {
                                            LucideIcon(
                                                if (listing.isBookmarked) {
                                                    LucideIcons.BookmarkCheck
                                                } else {
                                                    LucideIcons.Bookmark
                                                },
                                                contentDescription = null,
                                                modifier = Modifier.size(PoiskerIconSizes.Inline),
                                                tint = PoiskerColors.Primary,
                                            )
                                            Spacer(Modifier.width(6.dp))
                                            Text(if (listing.isBookmarked) "В закладках" else "В закладки")
                                        }
                                    }
                                    OutlinedButton(
                                        onClick = {
                                            val share = Intent(Intent.ACTION_SEND).apply {
                                                type = "text/plain"
                                                putExtra(
                                                    Intent.EXTRA_TEXT,
                                                    listing.publicUrl ?: listing.title,
                                                )
                                            }
                                            context.startActivity(
                                                Intent.createChooser(share, "Поделиться"),
                                            )
                                        },
                                        modifier = Modifier.weight(1f),
                                        shape = RoundedCornerShape(PoiskerRadius.md),
                                    ) {
                                        LucideIcon(
                                            LucideIcons.Share2,
                                            contentDescription = null,
                                            modifier = Modifier.size(PoiskerIconSizes.Inline),
                                        )
                                        Spacer(Modifier.width(6.dp))
                                        Text("Поделиться")
                                    }
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(PoiskerSpacing.xl))
                }
            }
        }
    }
}

@Composable
private fun ListingGallery(listing: ListingDto) {
    val images = listing.images.ifEmpty { listOfNotNull(listing.coverImage) }
    if (images.isEmpty()) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(4f / 3f)
                .background(PoiskerColors.Border),
            contentAlignment = Alignment.Center,
        ) {
            LucideIcon(
                LucideIcons.Image,
                contentDescription = null,
                modifier = Modifier.size(48.dp),
                tint = PoiskerColors.Muted,
            )
        }
        return
    }

    val pagerState = rememberPagerState(pageCount = { images.size })
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(PoiskerColors.Border),
    ) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(4f / 3f),
        ) { page ->
            AsyncImage(
                model = images[page],
                contentDescription = listing.title,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
        }
        if (images.size > 1) {
            Row(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = PoiskerSpacing.md)
                    .clip(RoundedCornerShape(20.dp))
                    .background(PoiskerColors.Text.copy(alpha = 0.45f))
                    .padding(horizontal = 10.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                repeat(images.size) { index ->
                    Box(
                        modifier = Modifier
                            .size(if (pagerState.currentPage == index) 8.dp else 6.dp)
                            .clip(CircleShape)
                            .background(
                                if (pagerState.currentPage == index) {
                                    PoiskerColors.Surface
                                } else {
                                    PoiskerColors.Surface.copy(alpha = 0.55f)
                                },
                            ),
                    )
                }
            }
            Text(
                text = "${pagerState.currentPage + 1}/${images.size}",
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(PoiskerSpacing.md)
                    .clip(RoundedCornerShape(8.dp))
                    .background(PoiskerColors.Text.copy(alpha = 0.55f))
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                color = PoiskerColors.Surface,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}

@Composable
private fun SafetyNote() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(PoiskerRadius.md))
            .background(PoiskerColors.WarningBg)
            .border(1.dp, PoiskerColors.WarningText.copy(alpha = 0.2f), RoundedCornerShape(PoiskerRadius.md))
            .padding(PoiskerSpacing.md),
        horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
        verticalAlignment = Alignment.Top,
    ) {
        Text(
            "Не переводите предоплату, пока не осмотрите товар и не убедитесь в надёжности продавца.",
            style = MaterialTheme.typography.bodySmall,
            color = PoiskerColors.WarningText,
            modifier = Modifier.weight(1f),
        )
    }
}
