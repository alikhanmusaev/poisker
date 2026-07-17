package ru.poisker.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.userMessage
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
    val infoMessage: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState())
    val state = _state.asStateFlow()

    fun setInfoMessage(message: String?) {
        _state.value = AuthUiState(infoMessage = message)
    }

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            _state.value = AuthUiState(error = "Введите email и пароль")
            return
        }
        viewModelScope.launch {
            _state.value = AuthUiState(isLoading = true)
            try {
                authRepository.login(email, password)
                _state.value = AuthUiState(success = true)
            } catch (e: ApiException) {
                _state.value = AuthUiState(error = e.userMessage())
            }
        }
    }

    fun register(
        displayName: String,
        email: String,
        phone: String,
        password: String,
        passwordConfirm: String,
        acceptTerms: Boolean,
        acceptPdn: Boolean,
    ) {
        when {
            displayName.isBlank() || email.isBlank() || phone.isBlank() || password.isBlank() ->
                _state.value = AuthUiState(error = "Заполните все поля")
            password.length < 8 ->
                _state.value = AuthUiState(error = "Пароль должен быть не короче 8 символов")
            password != passwordConfirm ->
                _state.value = AuthUiState(error = "Пароли не совпадают")
            !acceptTerms || !acceptPdn ->
                _state.value = AuthUiState(error = "Примите условия и согласие на обработку данных")
            else -> viewModelScope.launch {
                _state.value = AuthUiState(isLoading = true)
                try {
                    val user = authRepository.register(
                        displayName,
                        email,
                        phone,
                        password,
                        acceptTerms,
                        acceptPdn,
                    )
                    _state.value = AuthUiState(
                        infoMessage = "Аккаунт создан. Подтвердите email: ${user.email}",
                    )
                } catch (e: ApiException) {
                    _state.value = AuthUiState(error = e.userMessage())
                }
            }
        }
    }

    fun requestPasswordReset(email: String) {
        if (email.isBlank()) {
            _state.value = AuthUiState(error = "Введите email")
            return
        }
        viewModelScope.launch {
            _state.value = AuthUiState(isLoading = true)
            try {
                val message = authRepository.requestPasswordReset(email)
                _state.value = AuthUiState(infoMessage = message)
            } catch (e: ApiException) {
                _state.value = AuthUiState(error = e.userMessage())
            }
        }
    }

    fun resendVerification(email: String) {
        if (email.isBlank()) {
            _state.value = AuthUiState(error = "Введите email")
            return
        }
        viewModelScope.launch {
            _state.value = AuthUiState(isLoading = true)
            try {
                val message = authRepository.resendVerification(email)
                _state.value = AuthUiState(infoMessage = message)
            } catch (e: ApiException) {
                _state.value = AuthUiState(error = e.userMessage())
            }
        }
    }

    fun clearStatus() {
        _state.value = AuthUiState()
    }
}
