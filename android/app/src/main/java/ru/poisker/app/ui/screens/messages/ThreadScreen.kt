package ru.poisker.app.ui.screens.messages

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.data.remote.dto.ChatMessageDto
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.FullScreenLoading
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerIconSizes
import ru.poisker.app.ui.theme.PoiskerSpacing

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThreadScreen(
    conversationId: String?,
    listingId: String?,
    onBack: () -> Unit,
    viewModel: ThreadViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

    LaunchedEffect(conversationId, listingId) {
        when {
            !conversationId.isNullOrBlank() -> viewModel.load(conversationId)
            !listingId.isNullOrBlank() -> viewModel.startFromListing(listingId)
        }
    }

    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.lastIndex)
        }
    }

    val title = state.conversation?.post?.title ?: "Чат"
    val subtitle = state.conversation?.otherUser?.displayName

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(title, maxLines = 1)
                        subtitle?.let {
                            Text(it, style = MaterialTheme.typography.bodySmall, color = PoiskerColors.Muted)
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        LucideIcon(LucideIcons.ArrowLeft, contentDescription = "Назад")
                    }
                },
            )
        },
        bottomBar = {
            if (state.conversation != null) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(PoiskerColors.Surface)
                        .navigationBarsPadding()
                        .imePadding()
                        .padding(PoiskerSpacing.md),
                    horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = state.draft,
                        onValueChange = viewModel::updateDraft,
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Сообщение") },
                        maxLines = 4,
                    )
                    IconButton(
                        onClick = viewModel::send,
                        enabled = state.draft.isNotBlank() && !state.isSending,
                    ) {
                        if (state.isSending) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(PoiskerIconSizes.System),
                                color = PoiskerColors.Primary,
                                strokeWidth = 2.dp,
                            )
                        } else {
                            LucideIcon(LucideIcons.Send, contentDescription = "Отправить", tint = PoiskerColors.Primary)
                        }
                    }
                }
            }
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
            state.error != null && state.conversation == null -> ErrorBanner(
                state.error!!,
                Modifier.padding(padding).padding(PoiskerSpacing.lg),
            )
            else -> LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = PoiskerSpacing.lg),
                state = listState,
                verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm),
            ) {
                state.error?.let { item { ErrorBanner(it) } }
                if (state.messages.isEmpty()) {
                    item {
                        Text(
                            "Напишите первое сообщение",
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = PoiskerSpacing.xl),
                            color = PoiskerColors.Muted,
                        )
                    }
                }
                items(state.messages, key = { it.id }) { message ->
                    MessageBubble(message)
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessageDto) {
    val alignment = if (message.isMine) Alignment.CenterEnd else Alignment.CenterStart
    val background = if (message.isMine) PoiskerColors.PrimarySoft else PoiskerColors.Background
    val textColor = if (message.isMine) PoiskerColors.PrimaryDark else PoiskerColors.Text

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = alignment) {
        Column(
            modifier = Modifier
                .fillMaxWidth(0.82f)
                .background(background, RoundedCornerShape(12.dp))
                .padding(horizontal = PoiskerSpacing.md, vertical = PoiskerSpacing.sm),
        ) {
            if (!message.isMine) {
                Text(
                    message.sender.displayName,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = PoiskerColors.Muted,
                )
            }
            Text(
                message.body.ifBlank { "Фото" },
                color = textColor,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
