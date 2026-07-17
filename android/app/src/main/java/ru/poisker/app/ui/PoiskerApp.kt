package ru.poisker.app.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import ru.poisker.app.network.NetworkMonitor
import ru.poisker.app.web.WebViewStateHolder

@Composable
fun PoiskerApp(
    initialUrl: String? = null,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val networkMonitor = remember { NetworkMonitor(context) }
    val stateHolder = remember { WebViewStateHolder() }
    val startUrl = initialUrl?.takeIf { it.isNotBlank() } ?: ru.poisker.app.BuildConfig.START_URL

    WebViewScreen(
        startUrl = startUrl,
        stateHolder = stateHolder,
        networkMonitor = networkMonitor,
        modifier = modifier.fillMaxSize(),
    )
}
