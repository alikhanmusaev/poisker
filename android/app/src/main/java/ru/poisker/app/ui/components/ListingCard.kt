package ru.poisker.app.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import ru.poisker.app.data.remote.dto.ListingDto
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerRadius
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun ListingCard(
    listing: ListingDto,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(PoiskerRadius.md),
        colors = CardDefaults.cardColors(containerColor = PoiskerColors.Surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Row(modifier = Modifier.padding(PoiskerSpacing.md)) {
            AsyncImage(
                model = listing.coverImage,
                contentDescription = listing.title,
                modifier = Modifier
                    .height(88.dp)
                    .fillMaxWidth(0.32f)
                    .clip(RoundedCornerShape(PoiskerRadius.sm)),
                contentScale = ContentScale.Crop,
            )
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(start = PoiskerSpacing.md),
                verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.xs),
            ) {
                Text(
                    text = listing.title,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = listing.priceDisplay,
                    style = MaterialTheme.typography.titleSmall,
                    color = PoiskerColors.Primary,
                )
                Text(
                    text = "${listing.cityLabel} · ${listing.categoryLabel}",
                    style = MaterialTheme.typography.bodySmall,
                    color = PoiskerColors.Muted,
                )
            }
        }
    }
}

@Composable
fun ErrorBanner(message: String, modifier: Modifier = Modifier) {
    Text(
        text = message,
        color = PoiskerColors.Primary,
        style = MaterialTheme.typography.bodyMedium,
        modifier = modifier.padding(PoiskerSpacing.md),
    )
}
