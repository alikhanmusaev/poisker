package ru.poisker.app.push

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
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
        val notification = NotificationCompat.Builder(context, payload.channelId())
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
            .build()

        try {
            NotificationManagerCompat.from(context).notify(requestCode, notification)
        } catch (_: SecurityException) {
            // POST_NOTIFICATIONS denied — ignore.
        }
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
