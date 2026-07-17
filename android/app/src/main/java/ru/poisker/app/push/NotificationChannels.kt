package ru.poisker.app.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import ru.poisker.app.R

object NotificationChannels {
    const val MESSAGES = "messages"
    const val LISTINGS = "listings"
    const val SYSTEM = "system"

    fun ensureCreated(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channels = listOf(
            NotificationChannel(
                MESSAGES,
                context.getString(R.string.channel_messages),
                NotificationManager.IMPORTANCE_HIGH,
            ),
            NotificationChannel(
                LISTINGS,
                context.getString(R.string.channel_listings),
                NotificationManager.IMPORTANCE_DEFAULT,
            ),
            NotificationChannel(
                SYSTEM,
                context.getString(R.string.channel_system),
                NotificationManager.IMPORTANCE_DEFAULT,
            ),
        )
        channels.forEach { manager.createNotificationChannel(it) }
    }
}
