package ru.poisker.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.windowInsetsBottomHeight
import androidx.compose.foundation.layout.windowInsetsTopHeight
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import ru.poisker.app.network.NetworkMonitor
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.web.WebViewStateHolder

@Composable
fun PoiskerApp(
    initialUrl: String? = null,
    pendingNavigationUrl: String? = null,
    onNavigationConsumed: () -> Unit = {},
    onSessionLikelyReady: () -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val networkMonitor = remember { NetworkMonitor(context) }
    val stateHolder = remember { WebViewStateHolder() }
    val startUrl = initialUrl?.takeIf { it.isNotBlank() } ?: ru.poisker.app.BuildConfig.START_URL

    // Edge-to-edge draws under system bars; Android WebView does not fill
    // CSS env(safe-area-inset-*). Pad content and paint bar regions explicitly.
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(PoiskerColors.Background),
    ) {
        Spacer(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .windowInsetsTopHeight(WindowInsets.statusBars)
                .background(Color.White),
        )
        Spacer(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .windowInsetsBottomHeight(WindowInsets.navigationBars)
                .background(PoiskerColors.Background),
        )
        WebViewScreen(
            startUrl = startUrl,
            pendingNavigationUrl = pendingNavigationUrl,
            onNavigationConsumed = onNavigationConsumed,
            onSessionLikelyReady = onSessionLikelyReady,
            stateHolder = stateHolder,
            networkMonitor = networkMonitor,
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding(),
        )
    }
}
