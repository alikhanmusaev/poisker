package ru.poisker.app.ui.screens.messages

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import ru.poisker.app.data.remote.dto.ConversationDto
import ru.poisker.app.ui.components.EmptyState
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.PoiskerHeader
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MessagesScreen(
    onConversationClick: (String) -> Unit,
    onLoginRequired: () -> Unit,
    viewModel: MessagesViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        if (!viewModel.ensureAuth()) onLoginRequired()
        else viewModel.refresh()
    }

    if (!state.isAuthenticated) {
        Column(Modifier.fillMaxSize()) {
            PoiskerHeader()
            EmptyState(
                title = "Войдите в аккаунт",
                hint = "Переписки доступны после входа",
                actionLabel = "Войти",
                onAction = onLoginRequired,
            )
        }
        return
    }

    if (state.isLoading && state.conversations.isEmpty()) {
        Column(Modifier.fillMaxSize()) {
            PoiskerHeader()
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PoiskerColors.Primary)
            }
        }
        return
    }

    PullToRefreshBox(
        isRefreshing = state.isRefreshing,
        onRefresh = viewModel::refresh,
        modifier = Modifier.fillMaxSize(),
    ) {
        LazyColumn(contentPadding = PaddingValues(bottom = PoiskerSpacing.sm)) {
            item(key = "header") { PoiskerHeader() }
            item(key = "title") {
                Text(
                    "Сообщения",
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
            if (state.conversations.isEmpty()) {
                item {
                    EmptyState(
                        title = "Пока нет переписок",
                        hint = "Напишите продавцу из карточки объявления",
                    )
                }
            } else {
                items(state.conversations, key = { it.id }) { conversation ->
                    ConversationRow(
                        conversation = conversation,
                        onClick = { onConversationClick(conversation.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ConversationRow(
    conversation: ConversationDto,
    onClick: () -> Unit,
) {
    val preview = when {
        !conversation.lastMessageBody.isNullOrBlank() -> conversation.lastMessageBody
        !conversation.lastMessageImage.isNullOrBlank() -> "Фото"
        else -> "Нет сообщений"
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = PoiskerSpacing.lg, vertical = PoiskerSpacing.sm),
        horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (conversation.post.coverImage != null) {
            AsyncImage(
                model = conversation.post.coverImage,
                contentDescription = null,
                modifier = Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Crop,
            )
        } else {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(PoiskerColors.Background),
                contentAlignment = Alignment.Center,
            ) {
                LucideIcon(LucideIcons.Image, contentDescription = null, tint = PoiskerColors.Muted)
            }
        }
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text(
                conversation.post.title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                conversation.otherUser.displayName,
                style = MaterialTheme.typography.bodySmall,
                color = PoiskerColors.Muted,
            )
            Text(
                preview,
                style = MaterialTheme.typography.bodyMedium,
                color = if (conversation.unreadCount > 0) PoiskerColors.Text else PoiskerColors.Muted,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (conversation.unreadCount > 0) {
            Box(
                modifier = Modifier
                    .background(PoiskerColors.Primary, RoundedCornerShape(10.dp))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            ) {
                Text(
                    conversation.unreadCount.toString(),
                    color = PoiskerColors.Surface,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}
