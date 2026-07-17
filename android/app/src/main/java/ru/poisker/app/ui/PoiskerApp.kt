package ru.poisker.app.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.NavType
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import ru.poisker.app.ui.navigation.Routes
import ru.poisker.app.ui.screens.auth.LoginScreen
import ru.poisker.app.ui.screens.auth.RegisterScreen
import ru.poisker.app.ui.screens.bookmarks.BookmarksScreen
import ru.poisker.app.ui.screens.create.CreateListingScreen
import ru.poisker.app.ui.screens.details.DetailsScreen
import ru.poisker.app.ui.screens.home.HomeScreen
import ru.poisker.app.ui.screens.my.MyListingsScreen

private data class BottomItem(val route: String, val label: String, val icon: ImageVector)

@Composable
fun PoiskerApp() {
    val navController = rememberNavController()
    val bottomItems = listOf(
        BottomItem(Routes.HOME, "Главная", Icons.Default.Home),
        BottomItem(Routes.CREATE, "Подать", Icons.Default.Add),
        BottomItem(Routes.MY, "Мои", Icons.Default.Person),
        BottomItem(Routes.BOOKMARKS, "Избранное", Icons.Default.Favorite),
    )
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    val showBottomBar = currentRoute in bottomItems.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomItems.forEach { item ->
                        NavigationBarItem(
                            selected = currentRoute == item.route,
                            onClick = {
                                navController.navigate(item.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.HOME,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.HOME) {
                HomeScreen(onListingClick = { navController.navigate(Routes.details(it)) })
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
                )
            }
            composable(Routes.LOGIN) {
                LoginScreen(
                    onSuccess = { navController.popBackStack() },
                    onRegister = { navController.navigate(Routes.REGISTER) },
                )
            }
            composable(Routes.REGISTER) {
                RegisterScreen(onBack = { navController.popBackStack() })
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
            composable(Routes.MY) {
                MyListingsScreen(
                    onListingClick = { navController.navigate(Routes.details(it)) },
                    onLoginRequired = { navController.navigate(Routes.LOGIN) },
                )
            }
            composable(Routes.BOOKMARKS) {
                BookmarksScreen(onListingClick = { navController.navigate(Routes.details(it)) })
            }
        }
    }
}
