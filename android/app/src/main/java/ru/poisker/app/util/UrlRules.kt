package ru.poisker.app.util

import java.net.URI
import java.util.Locale

object UrlRules {
    const val PRIMARY_HOST = "poisker.ru"
    const val START_URL = "https://poisker.ru/"

    private val allowedHosts = setOf(
        "poisker.ru",
        "www.poisker.ru",
    )

    private val allowedSuffixes = listOf(
        ".poisker.ru",
    )

    private val externalSchemes = setOf(
        "tel",
        "mailto",
        "sms",
        "smsto",
        "geo",
        "market",
        "intent",
        "whatsapp",
        "tg",
        "viber",
        "skype",
    )

    fun isAllowedPoiskerHost(host: String?): Boolean {
        if (host.isNullOrBlank()) return false
        val normalized = host.lowercase(Locale.US).trimEnd('.')
        if (normalized in allowedHosts) return true
        return allowedSuffixes.any { normalized.endsWith(it) }
    }

    private fun parse(url: String): URI? =
        runCatching { URI(url.trim()) }.getOrNull()

    fun isInternalHttpUrl(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val uri = parse(url) ?: return false
        val scheme = uri.scheme?.lowercase(Locale.US) ?: return false
        if (scheme != "https" && scheme != "http") return false
        return isAllowedPoiskerHost(uri.host)
    }

    fun isExternalHttpUrl(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val uri = parse(url) ?: return false
        val scheme = uri.scheme?.lowercase(Locale.US) ?: return false
        if (scheme != "https" && scheme != "http") return false
        return !isAllowedPoiskerHost(uri.host)
    }

    fun isSpecialScheme(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val scheme = parse(url)?.scheme?.lowercase(Locale.US) ?: return false
        return scheme in externalSchemes
    }

    fun schemeOf(url: String?): String? =
        url?.let { parse(it)?.scheme?.lowercase(Locale.US) }

    fun shouldHandleInWebView(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        if (url.startsWith("about:blank", ignoreCase = true)) return true
        return isInternalHttpUrl(url)
    }
}
