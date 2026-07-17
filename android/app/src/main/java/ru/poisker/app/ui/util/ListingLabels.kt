package ru.poisker.app.ui.util

import ru.poisker.app.data.remote.dto.ListingDto

fun ListingDto.displayStatusLabel(): String? = statusLabel ?: when (status) {
    "draft" -> "Черновик"
    "pending" -> "На модерации"
    "published" -> "Опубликовано"
    "hidden" -> "Снято с публикации"
    "expired" -> "Истекло"
    "deleted" -> "Удалено"
    else -> null
}
