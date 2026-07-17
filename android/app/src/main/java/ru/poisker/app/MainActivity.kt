package ru.poisker.app

import android.Manifest
import android.app.AlertDialog
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
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import ru.poisker.app.push.NotificationChannels
import ru.poisker.app.push.NotificationSettingsOpener
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
    private var notificationDialogShownThisSession = false

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        lifecycleScope.launch {
            pushTokenManager.markNotificationPrompted()
            if (granted) {
                PushTokenSyncWorker.enqueue(this@MainActivity)
            } else {
                offerOpenNotificationSettings()
            }
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

    override fun onResume() {
        super.onResume()
        if (pushTokenManager.isLoggedInViaCookies() && hasNotificationPermission()) {
            PushTokenSyncWorker.enqueue(this)
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
            notificationDialogShownThisSession = false
        }
        wasLoggedIn = loggedIn
        maybeRequestNotificationsAndRegister()
    }

    private fun maybeRequestNotificationsAndRegister() {
        lifecycleScope.launch {
            if (!pushTokenManager.isLoggedInViaCookies()) return@launch
            PushTokenSyncWorker.enqueue(this@MainActivity)
            if (hasNotificationPermission()) return@launch
            if (notificationDialogShownThisSession) return@launch
            notificationDialogShownThisSession = true
            showNotificationEnableDialog()
        }
    }

    private fun showNotificationEnableDialog() {
        if (isFinishing || isDestroyed) return
        AlertDialog.Builder(this)
            .setTitle(R.string.notifications_dialog_title)
            .setMessage(R.string.notifications_dialog_message)
            .setPositiveButton(R.string.notifications_dialog_enable) { _, _ ->
                requestOrOpenNotificationPermission()
            }
            .setNegativeButton(R.string.notifications_dialog_later, null)
            .show()
    }

    private fun offerOpenNotificationSettings() {
        if (isFinishing || isDestroyed) return
        AlertDialog.Builder(this)
            .setTitle(R.string.notifications_denied_title)
            .setMessage(R.string.notifications_denied_message)
            .setPositiveButton(R.string.notifications_open_settings) { _, _ ->
                NotificationSettingsOpener.openAppNotificationSettings(this)
            }
            .setNegativeButton(R.string.notifications_dialog_later, null)
            .show()
    }

    private fun requestOrOpenNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            NotificationSettingsOpener.openAppNotificationSettings(this)
            return
        }
        val canAskAgain = ActivityCompat.shouldShowRequestPermissionRationale(
            this,
            Manifest.permission.POST_NOTIFICATIONS,
        )
        lifecycleScope.launch {
            val alreadyPrompted = pushTokenManager.wasNotificationPrompted()
            if (!alreadyPrompted || canAskAgain) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            } else {
                NotificationSettingsOpener.openAppNotificationSettings(this@MainActivity)
            }
        }
    }

    private fun hasNotificationPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED
    }
}
