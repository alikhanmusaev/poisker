package ru.poisker.app.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import ru.poisker.app.util.UrlRules

class PoiskerFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        PushTokenSyncWorker.enqueue(applicationContext, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val payload = if (data.isNotEmpty()) {
            PushPayload.fromData(data)
        } else {
            val notification = message.notification
            PushPayload(
                type = "system",
                title = notification?.title.orEmpty(),
                body = notification?.body.orEmpty(),
                url = UrlRules.START_URL,
            )
        }
        NotificationFactory.show(applicationContext, payload)
    }

    override fun onDeletedMessages() {
        // Server dropped messages — no-op.
    }
}
