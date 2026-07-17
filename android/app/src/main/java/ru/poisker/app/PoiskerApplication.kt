package ru.poisker.app

import android.app.Application
import android.webkit.CookieManager
import android.webkit.WebView
import ru.poisker.app.push.NotificationChannels

class PoiskerApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        CookieManager.getInstance().setAcceptCookie(true)
        NotificationChannels.ensureCreated(this)
        runCatching { WebView(this).destroy() }
    }
}
