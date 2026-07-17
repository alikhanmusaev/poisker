package ru.poisker.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** Colors from static/css/style.css :root tokens. */
object PoiskerColors {
    val Primary = Color(0xFFB91C1C) // --primary-700 / --color-primary
    val PrimaryHover = Color(0xFFDC2626) // --primary-600
    val PrimarySoft = Color(0xFFFEF2F2) // --primary-50
    val Background = Color(0xFFF8FAFC) // --slate-50 / --color-bg
    val Surface = Color(0xFFFFFFFF) // --color-surface
    val Text = Color(0xFF0F172A) // --slate-900
    val Muted = Color(0xFF64748B) // --slate-500
    val Border = Color(0xFFE2E8F0) // --slate-200
    val Danger = Color(0xFFEF4444) // --red-500
}

private val LightColors = lightColorScheme(
    primary = PoiskerColors.Primary,
    onPrimary = Color.White,
    primaryContainer = PoiskerColors.PrimarySoft,
    background = PoiskerColors.Background,
    surface = PoiskerColors.Surface,
    onBackground = PoiskerColors.Text,
    onSurface = PoiskerColors.Text,
    outline = PoiskerColors.Border,
    error = PoiskerColors.Danger,
)

private val PoiskerTypography = Typography(
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontSize = 14.sp,
        lineHeight = 20.sp,
        color = PoiskerColors.Muted,
    ),
)

@Composable
fun PoiskerTheme(content: @Composable () -> Unit) {
    // Site has no dark theme — keep light shell only.
    MaterialTheme(
        colorScheme = LightColors,
        typography = PoiskerTypography,
        content = content,
    )
}
