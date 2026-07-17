package ru.poisker.app.push

data class PushPayload(
    val type: String = "system",
    val title: String = "",
    val body: String = "",
    val url: String = "",
    val entityId: String = "",
) {
    companion object {
        const val EXTRA_URL = "push_url"
        const val EXTRA_TYPE = "push_type"
        const val EXTRA_ENTITY_ID = "push_entity_id"

        fun fromData(data: Map<String, String>): PushPayload {
            return PushPayload(
                type = data["type"].orEmpty().ifBlank { "system" },
                title = data["title"].orEmpty(),
                body = data["body"].orEmpty(),
                url = data["url"].orEmpty(),
                entityId = data["entity_id"].orEmpty(),
            )
        }
    }

    fun channelId(): String = when (type) {
        "message" -> NotificationChannels.MESSAGES
        "listing_approved",
        "listing_rejected",
        "listing_expiring",
        "listing_expired",
        -> NotificationChannels.LISTINGS
        else -> NotificationChannels.SYSTEM
    }
}
