package ru.poisker.app.ui.navigation

object Routes {
    const val HOME = "home"
    const val DETAILS = "details/{listingId}"
    const val LOGIN = "login"
    const val REGISTER = "register"
    const val PASSWORD_RESET = "password_reset"
    const val RESEND_VERIFICATION = "resend_verification"
    const val CREATE = "create"
    const val EDIT = "edit/{listingId}"
    const val PROFILE = "profile"
    const val BOOKMARKS = "bookmarks"
    const val MESSAGES = "messages"
    const val THREAD = "thread/{conversationId}"
    const val THREAD_START = "thread/start/{listingId}"

    fun details(id: String) = "details/$id"
    fun edit(id: String) = "edit/$id"
    fun thread(conversationId: String) = "thread/$conversationId"
    fun threadStart(listingId: String) = "thread/start/$listingId"
}
