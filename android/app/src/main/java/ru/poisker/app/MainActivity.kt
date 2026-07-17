package ru.poisker.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import ru.poisker.app.ui.PoiskerApp
import ru.poisker.app.ui.theme.PoiskerTheme
import ru.poisker.app.util.UrlRules

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val deepLinkUrl = extractDeepLink(intent)
        setContent {
            PoiskerTheme {
                PoiskerApp(initialUrl = deepLinkUrl)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // Deep links while running: reopen via recreate with new intent extras
        // is avoided — WebViewScreen reads start URL only once. Load in-place by
        // finishing and restarting is heavy; instead restart content.
        val url = extractDeepLink(intent) ?: return
        setContent {
            PoiskerTheme {
                PoiskerApp(initialUrl = url)
            }
        }
    }

    private fun extractDeepLink(intent: Intent?): String? {
        val data = intent?.data ?: return null
        val url = data.toString()
        return if (UrlRules.isInternalHttpUrl(url)) url else null
    }
}
