package ru.poisker.app.ui.components

import androidx.annotation.DrawableRes
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import ru.poisker.app.ui.navigation.Routes
import ru.poisker.app.ui.theme.PoiskerColors

private val NavBarContentHeight = 56.dp
private val FabSize = 44.dp

@Composable
fun PoiskerBottomBar(
    currentRoute: String?,
    isLoggedIn: Boolean,
    unreadMessages: Int = 0,
    onNavigate: (String) -> Unit,
) {
    if (isLoggedIn) {
        // FAB is a sibling of Surface so it can peek slightly above without
        // thickening the white bar (offset does not expand Surface layout).
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .zIndex(1f),
        ) {
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.BottomCenter),
                color = PoiskerColors.Surface,
                shadowElevation = 8.dp,
            ) {
                Column(modifier = Modifier.navigationBarsPadding()) {
                    HorizontalDivider(color = PoiskerColors.Border, thickness = 1.dp)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(NavBarContentHeight)
                            .padding(horizontal = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        BottomNavSlot(
                            modifier = Modifier.weight(1f),
                            selected = currentRoute == Routes.HOME,
                            label = "Главная",
                            icon = LucideIcons.LayoutGrid,
                            onClick = { onNavigate(Routes.HOME) },
                        )
                        BottomNavSlot(
                            modifier = Modifier.weight(1f),
                            selected = currentRoute == Routes.BOOKMARKS,
                            label = "Закладки",
                            icon = LucideIcons.Bookmark,
                            onClick = { onNavigate(Routes.BOOKMARKS) },
                        )
                        Box(
                            modifier = Modifier.weight(1f),
                            contentAlignment = Alignment.BottomCenter,
                        ) {
                            Text(
                                "Подать",
                                fontSize = 10.sp,
                                fontWeight = if (currentRoute == Routes.CREATE) {
                                    FontWeight.SemiBold
                                } else {
                                    FontWeight.Normal
                                },
                                color = if (currentRoute == Routes.CREATE) {
                                    PoiskerColors.Primary
                                } else {
                                    PoiskerColors.Muted
                                },
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(bottom = 6.dp),
                            )
                        }
                        BottomNavSlot(
                            modifier = Modifier.weight(1f),
                            selected = currentRoute == Routes.MESSAGES,
                            label = "Сообщения",
                            icon = LucideIcons.MessagesSquare,
                            badge = unreadMessages,
                            onClick = { onNavigate(Routes.MESSAGES) },
                        )
                        BottomNavSlot(
                            modifier = Modifier.weight(1f),
                            selected = currentRoute == Routes.PROFILE,
                            label = "Профиль",
                            icon = LucideIcons.User,
                            onClick = { onNavigate(Routes.PROFILE) },
                        )
                    }
                }
            }
            // Sits mostly inside the 56dp bar; only ~6dp peeks above.
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .navigationBarsPadding()
                    .padding(bottom = 12.dp)
                    .size(FabSize)
                    .shadow(3.dp, CircleShape)
                    .background(PoiskerColors.Primary, CircleShape)
                    .clickable { onNavigate(Routes.CREATE) },
                contentAlignment = Alignment.Center,
            ) {
                LucideIcon(
                    LucideIcons.Plus,
                    contentDescription = "Подать",
                    tint = PoiskerColors.Surface,
                )
            }
        }
    } else {
        Surface(color = PoiskerColors.Surface, shadowElevation = 8.dp) {
            Column(modifier = Modifier.navigationBarsPadding()) {
                HorizontalDivider(color = PoiskerColors.Border, thickness = 1.dp)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(NavBarContentHeight)
                        .padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    BottomNavSlot(
                        modifier = Modifier.weight(1f),
                        selected = currentRoute == Routes.HOME,
                        label = "Главная",
                        icon = LucideIcons.LayoutGrid,
                        onClick = { onNavigate(Routes.HOME) },
                    )
                    BottomNavSlot(
                        modifier = Modifier.weight(1f),
                        selected = currentRoute == Routes.LOGIN,
                        label = "Вход",
                        icon = LucideIcons.LogIn,
                        onClick = { onNavigate(Routes.LOGIN) },
                    )
                    BottomNavSlot(
                        modifier = Modifier.weight(1f),
                        selected = currentRoute == Routes.REGISTER,
                        label = "Регистрация",
                        icon = LucideIcons.UserPlus,
                        onClick = { onNavigate(Routes.REGISTER) },
                    )
                }
            }
        }
    }
}

@Composable
private fun BottomNavSlot(
    label: String,
    @DrawableRes icon: Int,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    badge: Int = 0,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp),
        modifier = modifier.clickable(onClick = onClick),
    ) {
        Box(contentAlignment = Alignment.TopEnd) {
            Box(
                modifier = Modifier
                    .background(
                        if (selected) PoiskerColors.PrimarySoft else PoiskerColors.Surface,
                        RoundedCornerShape(8.dp),
                    )
                    .padding(6.dp),
            ) {
                LucideIcon(
                    icon,
                    contentDescription = label,
                    tint = if (selected) PoiskerColors.Primary else PoiskerColors.Muted,
                )
            }
            if (badge > 0) {
                Box(
                    modifier = Modifier
                        .offset(x = 6.dp, y = (-4).dp)
                        .background(PoiskerColors.Primary, CircleShape)
                        .padding(horizontal = 5.dp, vertical = 1.dp),
                ) {
                    Text(
                        if (badge > 99) "99+" else badge.toString(),
                        color = PoiskerColors.Surface,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
        Text(
            label,
            fontSize = 10.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            color = if (selected) PoiskerColors.Primary else PoiskerColors.Muted,
            textAlign = TextAlign.Center,
            maxLines = 1,
        )
    }
}
