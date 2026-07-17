package ru.poisker.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerRadius
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun FullScreenLoading(
    message: String? = null,
) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(
                color = PoiskerColors.Primary,
                strokeWidth = 3.dp,
                modifier = Modifier.size(40.dp),
            )
            if (!message.isNullOrBlank()) {
                Spacer(Modifier.height(PoiskerSpacing.md))
                Text(message, color = PoiskerColors.Muted)
            }
        }
    }
}

@Composable
fun LoadingOverlay(
    visible: Boolean,
    modifier: Modifier = Modifier,
    message: String? = null,
) {
    if (!visible) return
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(PoiskerColors.Text.copy(alpha = 0.28f))
            .clickable(
                indication = null,
                interactionSource = remember { MutableInteractionSource() },
                onClick = {},
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier
                .background(PoiskerColors.Surface, RoundedCornerShape(PoiskerRadius.md))
                .padding(horizontal = PoiskerSpacing.xl, vertical = PoiskerSpacing.lg),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CircularProgressIndicator(
                color = PoiskerColors.Primary,
                strokeWidth = 3.dp,
                modifier = Modifier.size(36.dp),
            )
            if (!message.isNullOrBlank()) {
                Spacer(Modifier.height(PoiskerSpacing.sm))
                Text(message, color = PoiskerColors.Text)
            }
        }
    }
}

@Composable
fun LoadingButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    loading: Boolean = false,
    enabled: Boolean = true,
    containerColor: Color = PoiskerColors.Primary,
    contentColor: Color = PoiskerColors.Surface,
) {
    Button(
        onClick = onClick,
        modifier = modifier.fillMaxWidth(),
        enabled = enabled && !loading,
        shape = RoundedCornerShape(PoiskerRadius.md),
        colors = ButtonDefaults.buttonColors(
            containerColor = containerColor,
            contentColor = contentColor,
            disabledContainerColor = containerColor.copy(alpha = 0.7f),
            disabledContentColor = contentColor,
        ),
    ) {
        if (loading) {
            CircularProgressIndicator(
                modifier = Modifier.size(18.dp),
                color = contentColor,
                strokeWidth = 2.dp,
            )
            Spacer(Modifier.width(8.dp))
            Text("Загрузка…")
        } else {
            Text(text)
        }
    }
}

@Composable
fun InlineLoading(
    modifier: Modifier = Modifier,
    size: Int = 24,
) {
    Box(modifier = modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(
            color = PoiskerColors.Primary,
            strokeWidth = 2.dp,
            modifier = Modifier
                .padding(PoiskerSpacing.md)
                .size(size.dp),
        )
    }
}
