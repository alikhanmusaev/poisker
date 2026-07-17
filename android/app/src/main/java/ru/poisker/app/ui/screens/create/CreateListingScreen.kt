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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.ErrorBanner
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
    var category by rememberSaveable { mutableStateOf("elektronika") }
    var city by rememberSaveable { mutableStateOf("grozny") }
    var price by rememberSaveable { mutableStateOf("") }
    val imageUris = remember { mutableStateListOf<Uri>() }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        imageUris.clear()
        imageUris.addAll(uris.take(5))
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
        OutlinedTextField(body, { body = it }, label = { Text("Описание") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(category, { category = it }, label = { Text("Категория (slug)") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(city, { city = it }, label = { Text("Город (slug)") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(price, { price = it }, label = { Text("Цена") }, modifier = Modifier.fillMaxWidth())
        Button(onClick = { picker.launch("image/*") }) {
            Text("Фото: ${imageUris.size}")
        }
        state.error?.let { ErrorBanner(it) }
        if (state.isLoading) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = {
                    val files: List<File> = imageUris.mapNotNull { uri ->
                        runCatching {
                            context.contentResolver.openInputStream(uri)?.use { input ->
                                val file = File.createTempFile("upload", ".jpg", context.cacheDir)
                                file.outputStream().use { output -> input.copyTo(output) }
                                file
                            }
                        }.getOrNull()
                    }
                    viewModel.create(
                        title = title,
                        body = body,
                        category = category,
                        city = city,
                        price = price.toIntOrNull(),
                        files = files,
                        onSuccess = onCreated,
                        onAuthRequired = onLoginRequired,
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Отправить на модерацию")
            }
        }
    }
}
