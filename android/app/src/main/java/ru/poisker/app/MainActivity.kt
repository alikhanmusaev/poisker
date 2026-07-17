package ru.poisker.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import ru.poisker.app.push.NotificationChannels
import ru.poisker.app.push.PushNavigationHandler
import ru.poisker.app.push.PushTokenManager
import ru.poisker.app.push.PushTokenSyncWorker
import ru.poisker.app.push.PushUnregisterWorker
import ru.poisker.app.ui.PoiskerApp
import ru.poisker.app.ui.theme.PoiskerTheme

class MainActivity : ComponentActivity() {
    private var navigationUrl by mutableStateOf<String?>(null)
    private val pushTokenManager by lazy { PushTokenManager(applicationContext) }
    private var wasLoggedIn = false

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            PushTokenSyncWorker.enqueue(this)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        NotificationChannels.ensureCreated(this)
        navigationUrl = PushNavigationHandler.extractUrlFromIntent(intent)
        wasLoggedIn = pushTokenManager.isLoggedInViaCookies()
        setContent {
            PoiskerTheme {
                PoiskerApp(
                    initialUrl = navigationUrl,
                    onSessionLikelyReady = { onSessionTick() },
                    pendingNavigationUrl = navigationUrl,
                    onNavigationConsumed = { navigationUrl = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        navigationUrl = PushNavigationHandler.extractUrlFromIntent(intent)
    }

    private fun onSessionTick() {
        val loggedIn = pushTokenManager.isLoggedInViaCookies()
        if (wasLoggedIn && !loggedIn) {
            PushUnregisterWorker.enqueue(this)
        }
        wasLoggedIn = loggedIn
        maybeRequestNotificationsAndRegister()
    }

    private fun maybeRequestNotificationsAndRegister() {
        lifecycleScope.launch {
            if (!pushTokenManager.isLoggedInViaCookies()) return@launch
            PushTokenSyncWorker.enqueue(this@MainActivity)
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return@launch
            val granted = ContextCompat.checkSelfPermission(
                this@MainActivity,
                Manifest.permission.POST_NOTIFICATIONS,
            ) == PackageManager.PERMISSION_GRANTED
            if (granted) return@launch
            if (pushTokenManager.wasNotificationPrompted()) return@launch
            pushTokenManager.markNotificationPrompted()
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
