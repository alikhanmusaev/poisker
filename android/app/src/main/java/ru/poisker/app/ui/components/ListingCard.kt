package ru.poisker.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.ui.util.displayStatusLabel
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerRadius
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun ListingCard(
    listing: ListingDto,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    onBookmarkClick: (() -> Unit)? = null,
    showStatus: Boolean = false,
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(PoiskerRadius.md),
        colors = CardDefaults.cardColors(containerColor = PoiskerColors.Surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(4f / 3f)
                    .clip(RoundedCornerShape(topStart = PoiskerRadius.md, topEnd = PoiskerRadius.md))
                    .background(PoiskerColors.Border),
            ) {
                if (listing.coverImage != null) {
                    AsyncImage(
                        model = listing.coverImage,
                        contentDescription = listing.title,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop,
                    )
                } else {
                    LucideIcon(
                        LucideIcons.Image,
                        contentDescription = null,
                        modifier = Modifier
                            .align(Alignment.Center)
                            .size(40.dp),
                        tint = PoiskerColors.Muted,
                    )
                }
                if (onBookmarkClick != null) {
                    IconButton(
                        onClick = onBookmarkClick,
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(PoiskerSpacing.xs)
                            .size(36.dp)
                            .background(PoiskerColors.Surface.copy(alpha = 0.92f), CircleShape),
                    ) {
                        LucideIcon(
                            if (listing.isBookmarked) LucideIcons.BookmarkCheck else LucideIcons.Bookmark,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp),
                            tint = PoiskerColors.Primary,
                        )
                    }
                }
            }
            Column(
                modifier = Modifier.padding(PoiskerSpacing.md),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = listing.priceDisplay,
                    color = PoiskerColors.PrimaryDark,
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                )
                Text(
                    text = listing.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    lineHeight = 20.sp,
                )
                Text(
                    text = buildString {
                        append(if (listing.condition == "new") "Новый" else "Б/У")
                        append(" · ")
                        append(listing.cityLabel)
                        append(" · ")
                        append(listing.categoryLabel)
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = PoiskerColors.Muted,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (showStatus) {
                    listing.displayStatusLabel()?.let { StatusBadge(it, listing.status) }
                }
            }
        }
    }
}

@Composable
fun StatusBadge(label: String, status: String) {
    val bg = when (status) {
        "published" -> PoiskerColors.SuccessBg
        "draft" -> PoiskerColors.Border
        "pending" -> PoiskerColors.WarningBg
        "hidden", "expired" -> PoiskerColors.WarningBg
        else -> PoiskerColors.Border
    }
    val fg = when (status) {
        "published" -> PoiskerColors.SuccessText
        "pending" -> PoiskerColors.WarningText
        "hidden", "expired" -> PoiskerColors.WarningText
        else -> PoiskerColors.Muted
    }
    Text(
        text = label,
        modifier = Modifier
            .clip(RoundedCornerShape(PoiskerRadius.sm))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        style = MaterialTheme.typography.labelSmall,
        color = fg,
    )
}

@Composable
fun ErrorBanner(message: String, modifier: Modifier = Modifier) {
    Text(
        text = message,
        color = PoiskerColors.Danger,
        style = MaterialTheme.typography.bodyMedium,
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = PoiskerSpacing.md, vertical = PoiskerSpacing.sm),
    )
}

@Composable
fun EmptyState(
    title: String,
    hint: String,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(PoiskerSpacing.xl),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
    ) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text(hint, style = MaterialTheme.typography.bodyMedium, color = PoiskerColors.Muted)
        if (actionLabel != null && onAction != null) {
            androidx.compose.material3.Button(onClick = onAction) { Text(actionLabel) }
        }
    }
}
