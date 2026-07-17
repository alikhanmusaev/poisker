package ru.poisker.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.WifiOff
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import ru.poisker.app.R
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.web.PageError

@Composable
fun OfflineScreen(
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            imageVector = Icons.Outlined.WifiOff,
            contentDescription = null,
            modifier = Modifier.size(56.dp),
            tint = PoiskerColors.Muted,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = stringResource(R.string.offline_title),
            style = MaterialTheme.typography.titleLarge,
            color = PoiskerColors.Text,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.offline_message),
            style = MaterialTheme.typography.bodyMedium,
            color = PoiskerColors.Muted,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onRetry, modifier = Modifier.fillMaxWidth(0.7f)) {
            Text(stringResource(R.string.action_retry))
        }
    }
}

@Composable
fun ErrorScreen(
    error: PageError,
    onRetry: () -> Unit,
    onOpenInBrowser: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val (title, message, icon) = when (error) {
        is PageError.Network -> Triple(
            stringResource(R.string.error_network_title),
            error.description.ifBlank { stringResource(R.string.error_network_message) },
            Icons.Outlined.CloudOff,
        )
        is PageError.Http -> Triple(
            stringResource(R.string.error_http_title, error.code),
            stringResource(R.string.error_http_message),
            Icons.Outlined.ErrorOutline,
        )
        is PageError.Ssl -> Triple(
            stringResource(R.string.error_ssl_title),
            stringResource(R.string.error_ssl_message),
            Icons.Outlined.ErrorOutline,
        )
        is PageError.Unknown -> Triple(
            stringResource(R.string.error_unknown_title),
            error.description.ifBlank { stringResource(R.string.error_unknown_message) },
            Icons.Outlined.ErrorOutline,
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(56.dp),
            tint = PoiskerColors.Primary,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            color = PoiskerColors.Text,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = PoiskerColors.Muted,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onRetry, modifier = Modifier.fillMaxWidth(0.7f)) {
            Text(stringResource(R.string.action_retry))
        }
        if (onOpenInBrowser != null) {
            TextButton(onClick = onOpenInBrowser) {
                Text(stringResource(R.string.action_open_browser))
            }
        }
    }
}
