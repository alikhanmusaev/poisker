package ru.poisker.app.ui.screens.auth

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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun LoginScreen(
    onSuccess: () -> Unit,
    onRegister: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    LaunchedEffect(state.success) {
        if (state.success) {
            viewModel.clearStatus()
            onSuccess()
        }
    }

    AuthForm(
        title = "Вход",
        isLoading = state.isLoading,
        error = state.error,
        info = state.registerMessage,
        primaryLabel = "Войти",
        onPrimary = { viewModel.login(email, password) },
        footer = {
            TextButton(onClick = onRegister) { Text("Регистрация") }
        },
    ) {
        OutlinedTextField(email, { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(password, { password = it }, label = { Text("Пароль") }, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
fun RegisterScreen(
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var phone by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    AuthForm(
        title = "Регистрация",
        isLoading = state.isLoading,
        error = state.error,
        info = state.registerMessage,
        primaryLabel = "Создать аккаунт",
        onPrimary = { viewModel.register(name, email, phone, password) },
        footer = { TextButton(onClick = onBack) { Text("Уже есть аккаунт") } },
    ) {
        OutlinedTextField(name, { name = it }, label = { Text("Имя") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(email, { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(phone, { phone = it }, label = { Text("Телефон") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(password, { password = it }, label = { Text("Пароль") }, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun AuthForm(
    title: String,
    isLoading: Boolean,
    error: String?,
    info: String?,
    primaryLabel: String,
    onPrimary: () -> Unit,
    footer: @Composable () -> Unit,
    fields: @Composable () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(PoiskerSpacing.lg),
        verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.md),
    ) {
        Text(title)
        fields()
        error?.let { ErrorBanner(it) }
        info?.let { Text(it) }
        if (isLoading) {
            CircularProgressIndicator()
        } else {
            Button(onClick = onPrimary, modifier = Modifier.fillMaxWidth()) { Text(primaryLabel) }
        }
        footer()
    }
}
