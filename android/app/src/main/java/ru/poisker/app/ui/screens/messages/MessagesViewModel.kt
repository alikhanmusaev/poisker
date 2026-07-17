package ru.poisker.app.ui.screens.messages

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ConversationDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.MessagingRepository
import javax.inject.Inject

data class MessagesUiState(
    val isAuthenticated: Boolean = false,
    val conversations: List<ConversationDto> = emptyList(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class MessagesViewModel @Inject constructor(
    private val messagingRepository: MessagingRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MessagesUiState())
    val state = _state.asStateFlow()

    suspend fun ensureAuth(): Boolean {
        val loggedIn = authRepository.isLoggedIn.first()
        _state.update { it.copy(isAuthenticated = loggedIn) }
        return loggedIn
    }

    fun refresh() {
        viewModelScope.launch {
            if (!authRepository.isLoggedIn.first()) {
                _state.update { it.copy(isAuthenticated = false, isLoading = false) }
                return@launch
            }
            _state.update { it.copy(isRefreshing = true, error = null, isAuthenticated = true) }
            try {
                val response = messagingRepository.conversations()
                _state.update {
                    it.copy(
                        conversations = response.results,
                        isLoading = false,
                        isRefreshing = false,
                    )
                }
            } catch (e: ApiException) {
                val authFailed = e.code == "authentication_failed"
                _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message,
                        isAuthenticated = !authFailed,
                    )
                }
            }
        }
    }
}
