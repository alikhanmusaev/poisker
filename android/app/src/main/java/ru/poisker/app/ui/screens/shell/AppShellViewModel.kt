package ru.poisker.app.ui.screens.shell

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.poisker.app.data.repository.AuthRepository
import ru.poisker.app.data.repository.MessagingRepository
import javax.inject.Inject

@HiltViewModel
class AppShellViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
) : ViewModel() {
    val isLoggedIn = authRepository.isLoggedIn.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        false,
    )

    private val _unreadMessages = MutableStateFlow(0)
    val unreadMessages = _unreadMessages.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.isLoggedIn.collect { loggedIn ->
                if (loggedIn) refreshUnreadCount() else _unreadMessages.value = 0
            }
        }
    }

    fun refreshAuth() {
        viewModelScope.launch {
            runCatching { authRepository.refreshProfile() }
            refreshUnreadCount()
        }
    }

    fun refreshUnreadCount() {
        viewModelScope.launch {
            if (!authRepository.isLoggedIn.first()) {
                _unreadMessages.value = 0
                return@launch
            }
            runCatching { messagingRepository.unreadCount() }
                .onSuccess { _unreadMessages.value = it.count }
        }
    }
}
