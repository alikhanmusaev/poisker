package ru.poisker.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import ru.poisker.app.ui.components.PoiskerBottomBar
import ru.poisker.app.ui.components.PoiskerHeader
import ru.poisker.app.ui.navigation.Routes
import ru.poisker.app.ui.screens.auth.LoginScreen
import ru.poisker.app.ui.screens.auth.PasswordResetScreen
import ru.poisker.app.ui.screens.auth.RegisterScreen
import ru.poisker.app.ui.screens.auth.ResendVerificationScreen
import ru.poisker.app.ui.screens.bookmarks.BookmarksScreen
import ru.poisker.app.ui.screens.create.CreateListingScreen
import ru.poisker.app.ui.screens.details.DetailsScreen
import ru.poisker.app.ui.screens.edit.EditListingScreen
import ru.poisker.app.ui.screens.home.HomeScreen
import ru.poisker.app.ui.screens.messages.MessagesScreen
import ru.poisker.app.ui.screens.messages.ThreadScreen
import ru.poisker.app.ui.screens.profile.ProfileScreen
import ru.poisker.app.ui.screens.shell.AppShellViewModel

private val MAIN_ROUTES = setOf(
    Routes.HOME,
    Routes.BOOKMARKS,
    Routes.MESSAGES,
    Routes.PROFILE,
    Routes.CREATE,
    Routes.LOGIN,
    Routes.REGISTER,
)

private val HEADER_ROUTES = setOf(
    Routes.HOME,
    Routes.BOOKMARKS,
    Routes.MESSAGES,
    Routes.PROFILE,
)

@Composable
fun PoiskerApp(shellViewModel: AppShellViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route?.substringBefore("/")
    val isLoggedIn by shellViewModel.isLoggedIn.collectAsStateWithLifecycle(initialValue = false)
    val unreadMessages by shellViewModel.unreadMessages.collectAsStateWithLifecycle(initialValue = 0)
    val showBottomBar = currentRoute in MAIN_ROUTES
    val showHeader = currentRoute in HEADER_ROUTES

    Scaffold(
        topBar = {
            if (showHeader) {
                PoiskerHeader()
            }
        },
        bottomBar = {
            if (showBottomBar) {
                PoiskerBottomBar(
                    currentRoute = currentRoute,
                    isLoggedIn = isLoggedIn,
                    unreadMessages = unreadMessages,
                    onNavigate = { route ->
                        navController.navigate(route) {
                            popUpTo(navController.graph.startDestinationId) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                )
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.HOME,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.HOME) {
                HomeScreen(
                    onListingClick = { navController.navigate(Routes.details(it)) },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                )
            }
            composable(
                route = Routes.DETAILS,
                arguments = listOf(navArgument("listingId") { type = NavType.StringType }),
            ) { entry ->
                val id = entry.arguments?.getString("listingId").orEmpty()
                DetailsScreen(
                    listingId = id,
                    onBack = { navController.popBackStack() },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                    onEdit = { navController.navigate(Routes.edit(it)) },
                    onMessage = { navController.navigate(Routes.threadStart(it)) },
                )
            }
            composable(Routes.LOGIN) { entry ->
                val loginMessage by entry.savedStateHandle
                    .getStateFlow<String?>("login_message", null)
                    .collectAsStateWithLifecycle()
                LoginScreen(
                    initialInfo = loginMessage,
                    onSuccess = {
                        shellViewModel.refreshAuth()
                        if (!navController.popBackStack()) {
                            navController.navigate(Routes.PROFILE) {
                                popUpTo(navController.graph.startDestinationId) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    },
                    onRegister = { navController.navigate(Routes.REGISTER) },
                    onPasswordReset = { navController.navigate(Routes.PASSWORD_RESET) },
                    onResendVerification = { navController.navigate(Routes.RESEND_VERIFICATION) },
                )
            }
            composable(Routes.REGISTER) {
                RegisterScreen(
                    onBack = { navController.popBackStack() },
                    onRegistered = { email ->
                        val message = "Аккаунт создан. Подтвердите email: $email"
                        navController.navigate(Routes.LOGIN) {
                            popUpTo(Routes.REGISTER) { inclusive = true }
                            launchSingleTop = true
                        }
                        navController.currentBackStackEntry
                            ?.savedStateHandle
                            ?.set("login_message", message)
                    },
                )
            }
            composable(Routes.PASSWORD_RESET) {
                PasswordResetScreen(onBack = { navController.popBackStack() })
            }
            composable(Routes.RESEND_VERIFICATION) {
                ResendVerificationScreen(onBack = { navController.popBackStack() })
            }
            composable(Routes.CREATE) {
                CreateListingScreen(
                    onCreated = { id ->
                        navController.navigate(Routes.details(id)) {
                            popUpTo(Routes.HOME)
                        }
                    },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                )
            }
            composable(Routes.PROFILE) {
                ProfileScreen(
                    onListingClick = { navController.navigate(Routes.details(it)) },
                    onEditListing = { navController.navigate(Routes.edit(it)) },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                    onLoggedOut = {
                        shellViewModel.refreshAuth()
                        navController.navigate(Routes.HOME) {
                            popUpTo(navController.graph.startDestinationId) { inclusive = true }
                        }
                    },
                )
            }
            composable(Routes.BOOKMARKS) {
                BookmarksScreen(
                    onListingClick = { navController.navigate(Routes.details(it)) },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                )
            }
            composable(Routes.MESSAGES) {
                MessagesScreen(
                    onConversationClick = { navController.navigate(Routes.thread(it)) },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                )
            }
            composable(
                route = Routes.THREAD,
                arguments = listOf(navArgument("conversationId") { type = NavType.StringType }),
            ) { entry ->
                val id = entry.arguments?.getString("conversationId")
                ThreadScreen(
                    conversationId = id,
                    listingId = null,
                    onBack = {
                        shellViewModel.refreshUnreadCount()
                        navController.popBackStack()
                    },
                )
            }
            composable(
                route = Routes.THREAD_START,
                arguments = listOf(navArgument("listingId") { type = NavType.StringType }),
            ) { entry ->
                val id = entry.arguments?.getString("listingId")
                ThreadScreen(
                    conversationId = null,
                    listingId = id,
                    onBack = {
                        shellViewModel.refreshUnreadCount()
                        navController.popBackStack()
                    },
                )
            }
            composable(
                route = Routes.EDIT,
                arguments = listOf(navArgument("listingId") { type = NavType.StringType }),
            ) { entry ->
                val id = entry.arguments?.getString("listingId").orEmpty()
                EditListingScreen(
                    listingId = id,
                    onSaved = { navController.popBackStack() },
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }
}
