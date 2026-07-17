package ru.poisker.app

import android.app.Application
import android.webkit.CookieManager
import android.webkit.WebView

class PoiskerApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        CookieManager.getInstance().setAcceptCookie(true)
        // Warm WebView provider early to reduce first-paint jank.
        runCatching { WebView(this).destroy() }
    }
}
