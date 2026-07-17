package ru.poisker.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = PoiskerColors.Primary,
    onPrimary = Color.White,
    primaryContainer = PoiskerColors.PrimaryHover,
    background = PoiskerColors.Background,
    surface = PoiskerColors.Surface,
    onBackground = PoiskerColors.Text,
    onSurface = PoiskerColors.Text,
    outline = PoiskerColors.Border,
)

@Composable
fun PoiskerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content,
    )
}
