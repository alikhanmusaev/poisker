package ru.poisker.app.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val needsEmailVerification: Boolean = false,
    val success: Boolean = false,
    val registerMessage: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState())
    val state = _state.asStateFlow()

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _state.value = AuthUiState(isLoading = true)
            try {
                val user = authRepository.login(email, password)
                _state.value = AuthUiState(success = true)
                if (!user.emailVerified) {
                    _state.value = AuthUiState(needsEmailVerification = true)
                }
            } catch (e: ApiException) {
                _state.value = AuthUiState(error = e.message)
            }
        }
    }

    fun register(displayName: String, email: String, phone: String, password: String) {
        viewModelScope.launch {
            _state.value = AuthUiState(isLoading = true)
            try {
                val user = authRepository.register(displayName, email, phone, password)
                _state.value = AuthUiState(
                    registerMessage = "Аккаунт создан. Подтвердите email: ${user.email}",
                )
            } catch (e: ApiException) {
                _state.value = AuthUiState(error = e.fields?.values?.flatten()?.firstOrNull() ?: e.message)
            }
        }
    }

    fun clearStatus() {
        _state.value = AuthUiState()
    }
}
