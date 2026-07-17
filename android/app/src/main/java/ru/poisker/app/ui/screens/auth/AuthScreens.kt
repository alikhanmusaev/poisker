package ru.poisker.app.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.poisker.app.ui.components.ErrorBanner
import ru.poisker.app.ui.theme.PoiskerColors
import ru.poisker.app.ui.theme.PoiskerSpacing

@Composable
fun LoginScreen(
    onSuccess: () -> Unit,
    onRegister: () -> Unit,
    onPasswordReset: () -> Unit,
    onResendVerification: () -> Unit,
    initialInfo: String? = null,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    LaunchedEffect(initialInfo) {
        if (!initialInfo.isNullOrBlank()) {
            viewModel.setInfoMessage(initialInfo)
        }
    }

    LaunchedEffect(state.success) {
        if (state.success) {
            viewModel.clearStatus()
            onSuccess()
        }
    }

    AuthForm(
        title = "Вход",
        subtitle = "Войдите, чтобы публиковать и управлять объявлениями.",
        isLoading = state.isLoading,
        error = state.error,
        info = state.infoMessage,
        primaryLabel = "Войти",
        onPrimary = { viewModel.login(email, password) },
        footer = {
            Column(verticalArrangement = Arrangement.spacedBy(PoiskerSpacing.xs)) {
                TextButton(onClick = onPasswordReset, modifier = Modifier.fillMaxWidth()) {
                    Text("Забыли пароль?")
                }
                TextButton(onClick = onResendVerification, modifier = Modifier.fillMaxWidth()) {
                    Text("Не пришло письмо подтверждения?")
                }
                TextButton(onClick = onRegister, modifier = Modifier.fillMaxWidth()) {
                    Text("Регистрация")
                }
            }
        },
    ) {
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Пароль") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        )
    }
}

@Composable
fun RegisterScreen(
    onBack: () -> Unit,
    onRegistered: (String) -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var phone by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var passwordConfirm by rememberSaveable { mutableStateOf("") }
    var acceptTerms by rememberSaveable { mutableStateOf(false) }
    var acceptPdn by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(state.infoMessage) {
        val message = state.infoMessage ?: return@LaunchedEffect
        if (message.startsWith("Аккаунт создан")) {
            val registeredEmail = email.trim().lowercase()
            viewModel.clearStatus()
            onRegistered(registeredEmail)
        }
    }

    AuthForm(
        title = "Регистрация",
        subtitle = "После регистрации нужно подтвердить email.",
        isLoading = state.isLoading,
        error = state.error,
        info = null,
        primaryLabel = "Зарегистрироваться",
        onPrimary = {
            viewModel.register(name, email, phone, password, passwordConfirm, acceptTerms, acceptPdn)
        },
        primaryEnabled = acceptTerms && acceptPdn,
        footer = { TextButton(onClick = onBack) { Text("Уже есть аккаунт") } },
    ) {
        OutlinedTextField(name, { name = it }, label = { Text("Имя") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(
            email,
            { email = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        )
        OutlinedTextField(
            phone,
            { phone = it },
            label = { Text("Телефон") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
        )
        OutlinedTextField(
            password,
            { password = it },
            label = { Text("Пароль") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        )
        OutlinedTextField(
            passwordConfirm,
            { passwordConfirm = it },
            label = { Text("Повтор пароля") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = acceptTerms, onCheckedChange = { acceptTerms = it })
            Text("Принимаю условия использования", style = MaterialTheme.typography.bodySmall)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = acceptPdn, onCheckedChange = { acceptPdn = it })
            Text("Даю согласие на обработку персональных данных", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun PasswordResetScreen(
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf("") }

    AuthForm(
        title = "Забыли пароль?",
        subtitle = "Укажите email — мы отправим ссылку для создания нового пароля.",
        isLoading = state.isLoading,
        error = state.error,
        info = state.infoMessage,
        primaryLabel = "Отправить ссылку",
        onPrimary = { viewModel.requestPasswordReset(email) },
        footer = { TextButton(onClick = onBack) { Text("Вернуться ко входу") } },
    ) {
        OutlinedTextField(
            email,
            { email = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        )
    }
}

@Composable
fun ResendVerificationScreen(
    onBack: () -> Unit,
    initialEmail: String = "",
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var email by rememberSaveable { mutableStateOf(initialEmail) }

    AuthForm(
        title = "Подтверждение email",
        subtitle = "Отправим письмо повторно, если аккаунт ждёт подтверждения.",
        isLoading = state.isLoading,
        error = state.error,
        info = state.infoMessage,
        primaryLabel = "Отправить снова",
        onPrimary = { viewModel.resendVerification(email) },
        footer = { TextButton(onClick = onBack) { Text("Вернуться ко входу") } },
    ) {
        OutlinedTextField(
            email,
            { email = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        )
    }
}

@Composable
private fun AuthForm(
    title: String,
    subtitle: String,
    isLoading: Boolean,
    error: String?,
    info: String?,
    primaryLabel: String,
    onPrimary: () -> Unit,
    primaryEnabled: Boolean = true,
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
        Text(title, style = MaterialTheme.typography.headlineSmall)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = PoiskerColors.Muted)
        fields()
        error?.let { ErrorBanner(it) }
        info?.let { Text(it, color = PoiskerColors.SuccessText) }
        if (isLoading) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = onPrimary,
                modifier = Modifier.fillMaxWidth(),
                enabled = primaryEnabled,
            ) {
                Text(primaryLabel)
            }
        }
        footer()
    }
}
