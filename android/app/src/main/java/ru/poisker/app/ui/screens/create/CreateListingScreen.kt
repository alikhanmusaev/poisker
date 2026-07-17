package ru.poisker.app.ui.screens.create

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.CategoryPicker
import ru.poisker.app.ui.components.CityPicker
import ru.poisker.app.ui.components.ConditionPicker
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.components.ImagePreviewRow
import ru.poisker.app.ui.theme.PoiskerSpacing
import java.io.File

@Composable
fun CreateListingScreen(
    onCreated: (String) -> Unit,
    onLoginRequired: () -> Unit,
    viewModel: CreateListingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var title by rememberSaveable { mutableStateOf("") }
    var body by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("") }
    var city by rememberSaveable { mutableStateOf("") }
    var cityQuery by rememberSaveable { mutableStateOf("") }
    var condition by rememberSaveable { mutableStateOf("used") }
    var price by rememberSaveable { mutableStateOf("") }
    var coverIndex by rememberSaveable { mutableIntStateOf(0) }
    val imageUris = remember { mutableStateListOf<Uri>() }
    val imageFiles = remember { mutableStateListOf<File>() }

    LaunchedEffect(Unit) {
        if (!viewModel.ensureAuth()) onLoginRequired()
        else viewModel.loadCatalog()
    }

    LaunchedEffect(state.catalogLoaded, state.categories, state.cities) {
        if (!state.catalogLoaded) return@LaunchedEffect
        if (category.isBlank()) {
            category = state.categories.first().slug
        }
        if (city.isBlank()) {
            val defaultCity = state.cities.find { it.slug == "grozny" } ?: state.cities.first()
            city = defaultCity.slug
            cityQuery = defaultCity.label
        }
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        val remaining = 5 - imageFiles.size
        if (remaining <= 0) return@rememberLauncherForActivityResult
        uris.take(remaining).forEachIndexed { index, uri ->
            val file = runCatching {
                context.contentResolver.openInputStream(uri)?.use { input ->
                    val out = File.createTempFile("upload_${System.currentTimeMillis()}_$index", ".jpg", context.cacheDir)
                    out.outputStream().use { output -> input.copyTo(output) }
                    out
                }
            }.getOrNull()
            if (file != null) {
                imageUris.add(uri)
                imageFiles.add(file)
            }
        }
        if (coverIndex >= imageFiles.size) coverIndex = 0
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(PoiskerSpacing.lg),
        verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
    ) {
        Text("Новое объявление")
        OutlinedTextField(title, { title = it }, label = { Text("Заголовок") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(
            body,
            { body = it },
            label = { Text("Описание") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 4,
        )
        CategoryPicker(state.categories, category, onSelected = { category = it })
        CityPicker(
            cities = state.cities,
            selected = city,
            query = cityQuery,
            onQueryChange = {
                cityQuery = it
                viewModel.searchCities(it)
            },
            onSelected = { city = it },
        )
        Text("Состояние")
        ConditionPicker(condition) { condition = it }
        OutlinedTextField(price, { price = it }, label = { Text("Цена, ₽") }, modifier = Modifier.fillMaxWidth())
        OutlinedButton(onClick = { picker.launch("image/*") }, modifier = Modifier.fillMaxWidth()) {
            Text("Добавить фото (${imageFiles.size}/5)")
        }
        ImagePreviewRow(imageFiles, coverIndex, onSelectCover = { coverIndex = it })
        Text(
            "После отправки объявление попадёт на модерацию. Обычно это занимает немного времени.",
            style = androidx.compose.material3.MaterialTheme.typography.bodySmall,
        )
        state.error?.let { ErrorBanner(it) }
        if (state.isLoading) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = {
                    viewModel.create(
                        title = title,
                        body = body,
                        category = category,
                        city = city,
                        condition = condition,
                        price = price.toIntOrNull(),
                        files = imageFiles.toList(),
                        coverIndex = coverIndex,
                        onSuccess = onCreated,
                        onAuthRequired = onLoginRequired,
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = state.catalogLoaded && imageFiles.isNotEmpty() && title.isNotBlank() && body.isNotBlank(),
            ) {
                Text("Отправить на модерацию")
            }
        }
    }
}
