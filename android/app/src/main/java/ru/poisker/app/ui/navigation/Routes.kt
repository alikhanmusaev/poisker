package ru.poisker.app.ui.navigation

object Routes {
    const val HOME = "home"
    const val DETAILS = "details/{listingId}"
    const val LOGIN = "login"
    const val REGISTER = "register"
    const val CREATE = "create"
    const val EDIT = "edit/{listingId}"
    const val MY = "my"
    const val BOOKMARKS = "bookmarks"

    fun details(id: String) = "details/$id"
    fun edit(id: String) = "edit/$id"
}
