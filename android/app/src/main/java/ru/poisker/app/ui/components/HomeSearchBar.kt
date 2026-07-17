package ru.poisker.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn

import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.VerticalDivider
import ru.poisker.app.ui.icons.LucideIcon
import ru.poisker.app.ui.icons.LucideIcons
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerRadius
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun HomeSearchBar(
    search: String,
    onSearchChange: (String) -> Unit,
    selectedCity: String?,
    selectedCityLabel: String,
    cityPanelQuery: String,
    citySuggestions: List<CityDto>,
    isCitySearching: Boolean,
    onCityPanelQueryChange: (String) -> Unit,
    onCitySelect: (slug: String, label: String) -> Unit,
    onCityClear: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var cityPanelOpen by remember { mutableStateOf(false) }
    val searchInteraction = remember { MutableInteractionSource() }
    val searchFocused by searchInteraction.collectIsFocusedAsState()
    val cityPanelFocusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current
    val barShape = RoundedCornerShape(PoiskerRadius.md)
    val barFocused = searchFocused || cityPanelOpen

    Box(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .clip(barShape)
                .border(
                    width = 1.dp,
                    color = if (barFocused) PoiskerColors.Primary else PoiskerColors.Border,
                    shape = barShape,
                )
                .background(PoiskerColors.Surface),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp)
                    .padding(start = PoiskerSpacing.md),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                LucideIcon(
                    LucideIcons.Search,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                    tint = PoiskerColors.Muted,
                )
                BasicTextField(
                    value = search,
                    onValueChange = onSearchChange,
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = PoiskerSpacing.sm),
                    textStyle = MaterialTheme.typography.bodyLarge.copy(color = PoiskerColors.Text),
                    singleLine = true,
                    interactionSource = searchInteraction,
                    cursorBrush = SolidColor(PoiskerColors.Primary),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    decorationBox = { inner ->
                        Box(contentAlignment = Alignment.CenterStart) {
                            if (search.isEmpty()) {
                                Text(
                                    "iPhone, квартира, автомобиль…",
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = PoiskerColors.Muted,
                                )
                            }
                            inner()
                        }
                    },
                )
            }

            VerticalDivider(
                modifier = Modifier.height(32.dp),
                color = PoiskerColors.Border,
            )

            Row(
                modifier = Modifier
                    .widthIn(min = 108.dp, max = 148.dp)
                    .height(48.dp)
                    .clickable {
                        cityPanelOpen = !cityPanelOpen
                        if (cityPanelOpen) {
                            onCityPanelQueryChange(selectedCityLabel)
                        }
                    }
                    .padding(start = PoiskerSpacing.sm, end = PoiskerSpacing.sm),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                LucideIcon(
                    LucideIcons.MapPin,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = if (selectedCity != null) PoiskerColors.PrimaryDark else PoiskerColors.Muted,
                )
                Text(
                    text = selectedCityLabel.ifBlank { "Город" },
                    modifier = Modifier.weight(1f, fill = false),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    softWrap = false,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = if (selectedCity != null) PoiskerColors.PrimaryDark else PoiskerColors.Muted,
                )
                LucideIcon(
                    LucideIcons.ChevronDown,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = PoiskerColors.Muted,
                )
            }
        }

        if (cityPanelOpen) {
            Popup(
                alignment = Alignment.TopEnd,
                offset = IntOffset(0, 56),
                onDismissRequest = {
                    cityPanelOpen = false
                    focusManager.clearFocus()
                },
                properties = PopupProperties(focusable = true),
            ) {
                Surface(
                    modifier = Modifier.widthIn(min = 280.dp, max = 360.dp),
                    shape = RoundedCornerShape(14.dp),
                    shadowElevation = 12.dp,
                    color = PoiskerColors.Surface,
                    border = androidx.compose.foundation.BorderStroke(1.dp, PoiskerColors.Border),
                ) {
                    Column(modifier = Modifier.padding(PoiskerSpacing.md)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Населённый пункт",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                                color = PoiskerColors.Muted,
                            )
                            if (selectedCity != null) {
                                TextButton(onClick = {
                                    onCityClear()
                                    cityPanelOpen = false
                                    focusManager.clearFocus()
                                }) {
                                    Text("Сбросить", color = PoiskerColors.Primary)
                                }
                            }
                        }

                        BasicTextField(
                            value = cityPanelQuery,
                            onValueChange = onCityPanelQueryChange,
                            modifier = Modifier
                                .fillMaxWidth()
                                .focusRequester(cityPanelFocusRequester)
                                .padding(top = PoiskerSpacing.sm)
                                .height(44.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .border(1.dp, PoiskerColors.Border, RoundedCornerShape(10.dp))
                                .background(PoiskerColors.Surface)
                                .padding(horizontal = PoiskerSpacing.md),
                            textStyle = MaterialTheme.typography.bodyLarge.copy(color = PoiskerColors.Text),
                            singleLine = true,
                            cursorBrush = SolidColor(PoiskerColors.Primary),
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                            keyboardActions = KeyboardActions(onDone = { focusManager.clearFocus() }),
                            decorationBox = { inner ->
                                Box(contentAlignment = Alignment.CenterStart) {
                                    if (cityPanelQuery.isEmpty()) {
                                        Text(
                                            "Начните вводить название…",
                                            style = MaterialTheme.typography.bodyLarge,
                                            color = PoiskerColors.Muted,
                                        )
                                    }
                                    inner()
                                }
                            },
                        )

                        when {
                            isCitySearching -> Box(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(PoiskerSpacing.md),
                                contentAlignment = Alignment.Center,
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    color = PoiskerColors.Primary,
                                    strokeWidth = 2.dp,
                                )
                            }
                            cityPanelQuery.isBlank() -> Unit
                            citySuggestions.isEmpty() -> Text(
                                "Ничего не найдено",
                                modifier = Modifier.padding(top = PoiskerSpacing.md),
                                style = MaterialTheme.typography.bodyMedium,
                                color = PoiskerColors.Muted,
                            )
                            else -> LazyColumn(
                                modifier = Modifier
                                    .padding(top = PoiskerSpacing.sm)
                                    .heightIn(max = 240.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .border(1.dp, PoiskerColors.Border, RoundedCornerShape(10.dp)),
                            ) {
                                itemsIndexed(citySuggestions, key = { _, city -> city.slug }) { index, city ->
                                    Text(
                                        text = city.label,
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable {
                                                onCitySelect(city.slug, city.label)
                                                cityPanelOpen = false
                                                focusManager.clearFocus()
                                            }
                                            .padding(horizontal = PoiskerSpacing.md, vertical = 12.dp),
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = PoiskerColors.Text,
                                    )
                                    if (index < citySuggestions.lastIndex) {
                                        HorizontalDivider(color = PoiskerColors.Border)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            androidx.compose.runtime.LaunchedEffect(cityPanelOpen) {
                if (cityPanelOpen) {
                    cityPanelFocusRequester.requestFocus()
                }
            }
        }
    }
}
