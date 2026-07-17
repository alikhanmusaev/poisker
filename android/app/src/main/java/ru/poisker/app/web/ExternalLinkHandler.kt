package ru.poisker.app.web

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import ru.poisker.app.R
import ru.poisker.app.util.UrlRules

object ExternalLinkHandler {
    fun open(context: Context, url: String): Boolean {
        return try {
            when {
                url.startsWith("tel:", ignoreCase = true) -> {
                    context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse(url)))
                    true
                }
                url.startsWith("mailto:", ignoreCase = true) ||
                    url.startsWith("sms:", ignoreCase = true) ||
                    url.startsWith("smsto:", ignoreCase = true) ||
                    url.startsWith("geo:", ignoreCase = true) ||
                    url.startsWith("market:", ignoreCase = true) -> {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    true
                }
                url.startsWith("intent:", ignoreCase = true) -> openIntentUrl(context, url)
                url.startsWith("whatsapp:", ignoreCase = true) ->
                    openAppOrFallback(context, url, httpsFallback = whatsappHttpsFallback(url))
                url.startsWith("tg:", ignoreCase = true) ->
                    openAppOrFallback(context, url, httpsFallback = telegramHttpsFallback(url))
                UrlRules.isExternalHttpUrl(url) -> {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    true
                }
                else -> {
                    // Unknown scheme: do not crash.
                    Toast.makeText(context, R.string.link_unsupported, Toast.LENGTH_SHORT).show()
                    true
                }
            }
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(context, R.string.link_unsupported, Toast.LENGTH_SHORT).show()
            true
        } catch (_: Exception) {
            Toast.makeText(context, R.string.link_unsupported, Toast.LENGTH_SHORT).show()
            true
        }
    }

    private fun openIntentUrl(context: Context, url: String): Boolean {
        return try {
            val intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME)
            try {
                context.startActivity(intent)
                true
            } catch (_: ActivityNotFoundException) {
                val fallback = intent.getStringExtra("browser_fallback_url")
                if (!fallback.isNullOrBlank()) {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(fallback)))
                    true
                } else {
                    Toast.makeText(context, R.string.link_unsupported, Toast.LENGTH_SHORT).show()
                    true
                }
            }
        } catch (_: Exception) {
            Toast.makeText(context, R.string.link_unsupported, Toast.LENGTH_SHORT).show()
            true
        }
    }

    private fun openAppOrFallback(context: Context, deepLink: String, httpsFallback: String?): Boolean {
        return try {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(deepLink)))
            true
        } catch (_: ActivityNotFoundException) {
            if (!httpsFallback.isNullOrBlank()) {
                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(httpsFallback)))
                true
            } else {
                Toast.makeText(context, R.string.app_not_installed, Toast.LENGTH_SHORT).show()
                true
            }
        }
    }

    private fun whatsappHttpsFallback(url: String): String? {
        val uri = Uri.parse(url)
        val phone = uri.getQueryParameter("phone")
            ?: uri.schemeSpecificPart?.substringAfter("send?phone=")?.substringBefore('&')
        val text = uri.getQueryParameter("text")
        return when {
            !phone.isNullOrBlank() -> {
                val builder = Uri.parse("https://wa.me/$phone").buildUpon()
                if (!text.isNullOrBlank()) builder.appendQueryParameter("text", text)
                builder.build().toString()
            }
            else -> "https://wa.me/"
        }
    }

    private fun telegramHttpsFallback(url: String): String? {
        val uri = Uri.parse(url)
        val path = uri.schemeSpecificPart?.removePrefix("//")?.trim('/')
        return when {
            path.isNullOrBlank() -> "https://t.me/"
            path.startsWith("resolve?") -> {
                val domain = Uri.parse("tg://$path").getQueryParameter("domain")
                if (!domain.isNullOrBlank()) "https://t.me/$domain" else "https://t.me/"
            }
            else -> "https://t.me/$path"
        }
    }
}
