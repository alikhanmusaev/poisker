package ru.poisker.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import ru.poisker.app.data.remote.dto.CategoryDto
import ru.poisker.app.data.remote.dto.CityDto
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerRadius
import ru.poisker.app.ui.theme.PoiskerSpacing
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CategoryPicker(
    categories: List<CategoryDto>,
    selected: String,
    onSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    val label = categories.find { it.slug == selected }?.label ?: "Выберите категорию"
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }, modifier = modifier) {
        OutlinedTextField(
            value = label,
            onValueChange = {},
            readOnly = true,
            label = { Text("Категория") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            categories.forEach { category ->
                DropdownMenuItem(
                    text = { Text(category.label) },
                    onClick = {
                        onSelected(category.slug)
                        expanded = false
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CityPicker(
    cities: List<CityDto>,
    selected: String,
    query: String,
    onQueryChange: (String) -> Unit,
    onSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    val label = cities.find { it.slug == selected }?.label
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }, modifier = modifier) {
        OutlinedTextField(
            value = if (expanded) query else (label ?: query),
            onValueChange = {
                onQueryChange(it)
                expanded = true
            },
            label = { Text("Город") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            cities.take(15).forEach { city ->
                DropdownMenuItem(
                    text = { Text(city.label) },
                    onClick = {
                        onSelected(city.slug)
                        onQueryChange(city.label)
                        expanded = false
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ConditionPicker(selected: String, onSelected: (String) -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
        listOf("used" to "Б/У", "new" to "Новый").forEach { (value, label) ->
            val active = selected == value
            Text(
                text = label,
                modifier = Modifier
                    .clip(RoundedCornerShape(PoiskerRadius.sm))
                    .background(if (active) PoiskerColors.PrimarySoft else PoiskerColors.Surface)
                    .border(
                        1.dp,
                        if (active) PoiskerColors.Primary else PoiskerColors.Border,
                        RoundedCornerShape(PoiskerRadius.sm),
                    )
                    .clickable { onSelected(value) }
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                color = if (active) PoiskerColors.Primary else PoiskerColors.Text,
            )
        }
    }
}

@Composable
fun ImagePreviewRow(
    imageFiles: List<File>,
    coverIndex: Int,
    onSelectCover: (Int) -> Unit,
) {
    if (imageFiles.isEmpty()) return
    LazyRow(horizontalArrangement = Arrangement.spacedBy(PoiskerSpacing.sm)) {
        itemsIndexed(imageFiles) { index, file ->
            Box(
                modifier = Modifier
                    .size(88.dp)
                    .clip(RoundedCornerShape(PoiskerRadius.sm))
                    .border(
                        width = if (index == coverIndex) 2.dp else 0.dp,
                        color = PoiskerColors.Primary,
                        shape = RoundedCornerShape(PoiskerRadius.sm),
                    )
                    .clickable { onSelectCover(index) },
            ) {
                AsyncImage(
                    model = file,
                    contentDescription = null,
                    modifier = Modifier.fillMaxWidth().height(88.dp),
                    contentScale = ContentScale.Crop,
                )
            }
        }
    }
}
