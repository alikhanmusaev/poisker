package ru.poisker.app.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

object PoiskerColors {
    val Primary = Color(0xFFB91C1C)
    val PrimaryDark = Color(0xFF991B1B)
    val PrimaryHover = Color(0xFFDC2626)
    val PrimarySoft = Color(0xFFFEF2F2)
    val Background = Color(0xFFF8FAFC)
    val Surface = Color(0xFFFFFFFF)
    val Text = Color(0xFF0F172A)
    val Muted = Color(0xFF64748B)
    val Border = Color(0xFFE2E8F0)
    val Danger = Color(0xFFEF4444)
    val SuccessBg = Color(0xFFF0FDF4)
    val SuccessText = Color(0xFF166534)
    val WarningBg = Color(0xFFFFFBEB)
    val WarningText = Color(0xFFB45309)
}

object PoiskerSpacing {
    val xs = 4.dp
    val sm = 8.dp
    val md = 12.dp
    val lg = 16.dp
    val xl = 24.dp
}

/**
 * Material / Google icon sizing.
 * System icon: 24dp. IconButton touch target: 48dp → 12dp padding around the icon.
 * Navigation active indicator: 64×32dp with a centered 24dp icon.
 * Standard FAB: 56dp with 24dp icon → 16dp padding.
 * Button / chip leading icons: 18dp (Material3 defaults).
 */
object PoiskerIconSizes {
    val System = 24.dp
    val Dense = 20.dp
    val Inline = 18.dp
    val TouchTarget = 48.dp
    val IconButtonPadding = 12.dp
    val NavIndicatorWidth = 64.dp
    val NavIndicatorHeight = 32.dp
    val Fab = 56.dp
    val FabPadding = 16.dp
}

object PoiskerRadius {
    val sm = 8.dp
    val md = 12.dp
    val lg = 16.dp
}
