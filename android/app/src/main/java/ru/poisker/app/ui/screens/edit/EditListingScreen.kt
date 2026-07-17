package ru.poisker.app.ui.screens.edit

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.CategoryPicker
import ru.poisker.app.ui.components.CityPicker
import ru.poisker.app.ui.components.ConditionPicker
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing
import ru.poisker.app.ui.util.displayStatusLabel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditListingScreen(
    listingId: String,
    onSaved: () -> Unit,
    onBack: () -> Unit,
    viewModel: EditListingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var title by rememberSaveable { mutableStateOf("") }
    var body by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("") }
    var city by rememberSaveable { mutableStateOf("") }
    var cityQuery by rememberSaveable { mutableStateOf("") }
    var condition by rememberSaveable { mutableStateOf("used") }
    var price by rememberSaveable { mutableStateOf("") }
    var initialized by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(listingId) {
        initialized = false
        viewModel.load(listingId)
    }

    LaunchedEffect(state.listing, listingId) {
        val listing = state.listing
        if (listing != null && listing.id == listingId && !initialized) {
            title = listing.title
            body = listing.body.orEmpty()
            category = listing.category
            city = listing.city
            cityQuery = listing.cityLabel
            condition = listing.condition
            price = listing.price?.toString().orEmpty()
            initialized = true
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Редактирование") },
                navigationIcon = {
                    androidx.compose.material3.TextButton(onClick = onBack) { Text("Назад") }
                },
            )
        },
    ) { padding ->
        when {
            state.isLoading && state.listing == null -> Box(
                Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = PoiskerColors.Primary)
            }
            else -> Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(PoiskerSpacing.lg),
                verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
            ) {
                state.listing?.displayStatusLabel()?.let { Text("Статус: $it") }
                OutlinedTextField(title, { title = it }, label = { Text("Заголовок") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(body, { body = it }, label = { Text("Описание") }, modifier = Modifier.fillMaxWidth(), minLines = 4)
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
                ConditionPicker(condition) { condition = it }
                OutlinedTextField(price, { price = it }, label = { Text("Цена, ₽") }, modifier = Modifier.fillMaxWidth())
                state.error?.let { ErrorBanner(it) }
                Button(
                    onClick = {
                        viewModel.save(
                            id = listingId,
                            title = title,
                            body = body,
                            category = category,
                            city = city,
                            condition = condition,
                            price = price.toIntOrNull(),
                            onSaved = onSaved,
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.isLoading,
                ) {
                    Text("Сохранить")
                }
            }
        }
    }
}
