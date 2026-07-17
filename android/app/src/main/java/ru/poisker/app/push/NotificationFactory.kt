package ru.poisker.app.push

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.graphics.createBitmap
import ru.poisker.app.MainActivity
import ru.poisker.app.R
import ru.poisker.app.util.UrlRules

object NotificationFactory {
    fun show(context: Context, payload: PushPayload) {
        NotificationChannels.ensureCreated(context)
        val safeUrl = PushNavigationHandler.sanitizeUrl(payload.url)
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(PushPayload.EXTRA_URL, safeUrl)
            putExtra(PushPayload.EXTRA_TYPE, payload.type)
            putExtra(PushPayload.EXTRA_ENTITY_ID, payload.entityId)
        }
        val requestCode = (safeUrl + payload.type + payload.entityId).hashCode()
        val pending = PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val title = payload.title.ifBlank { context.getString(R.string.app_name) }
        val body = payload.body.ifBlank { context.getString(R.string.push_default_body) }
        val builder = NotificationCompat.Builder(context, payload.channelId())
            .setSmallIcon(R.drawable.ic_stat_poisker)
            .setColor(ContextCompat.getColor(context, R.color.poisker_primary))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(pending)
            .setPriority(
                if (payload.type == "message") {
                    NotificationCompat.PRIORITY_HIGH
                } else {
                    NotificationCompat.PRIORITY_DEFAULT
                },
            )
        largeAppIcon(context)?.let { builder.setLargeIcon(it) }

        try {
            NotificationManagerCompat.from(context).notify(requestCode, builder.build())
        } catch (_: SecurityException) {
            // POST_NOTIFICATIONS denied — ignore.
        }
    }

    private fun largeAppIcon(context: Context): Bitmap? {
        // Full-color brand mark in the notification body (smallIcon stays monochrome vector).
        val drawable = ContextCompat.getDrawable(context, R.drawable.ic_notification_large)
            ?: ContextCompat.getDrawable(context, R.mipmap.ic_launcher)
            ?: return null
        val size = (64 * context.resources.displayMetrics.density).toInt().coerceAtLeast(128)
        val bitmap = createBitmap(size, size)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, size, size)
        drawable.draw(canvas)
        return bitmap
    }
}

object PushNavigationHandler {
    fun sanitizeUrl(raw: String?): String {
        val candidate = raw?.trim().orEmpty()
        if (!UrlRules.isInternalHttpUrl(candidate)) return UrlRules.START_URL
        // Push deep links must be HTTPS only.
        return if (candidate.startsWith("https://", ignoreCase = true)) {
            candidate
        } else {
            UrlRules.START_URL
        }
    }

    fun extractUrlFromIntent(intent: Intent?): String? {
        if (intent == null) return null
        val fromExtra = intent.getStringExtra(PushPayload.EXTRA_URL)
        if (!fromExtra.isNullOrBlank()) {
            return sanitizeUrl(fromExtra)
        }
        val data = intent.data?.toString()
        return if (UrlRules.isInternalHttpUrl(data)) data else null
    }
}
