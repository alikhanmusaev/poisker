package ru.poisker.app.ui.screens.messages

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import ru.poisker.app.data.remote.dto.ChatMessageDto
import ru.poisker.app.data.remote.dto.ConversationDto
import ru.poisker.app.data.repository.ApiException
import ru.poisker.app.data.repository.MessagingRepository
import javax.inject.Inject

data class ThreadUiState(
    val conversation: ConversationDto? = null,
    val messages: List<ChatMessageDto> = emptyList(),
    val draft: String = "",
    val isLoading: Boolean = true,
    val isSending: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ThreadViewModel @Inject constructor(
    private val messagingRepository: MessagingRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ThreadUiState())
    val state = _state.asStateFlow()

    fun load(conversationId: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val conversation = messagingRepository.conversation(conversationId)
                _state.update {
                    it.copy(
                        conversation = conversation,
                        messages = conversation.messages,
                        isLoading = false,
                    )
                }
            } catch (e: ApiException) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun startFromListing(listingId: String) {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                val conversation = messagingRepository.startConversation(listingId)
                _state.update {
                    it.copy(
                        conversation = conversation,
                        messages = conversation.messages,
                        isLoading = false,
                    )
                }
            } catch (e: ApiException) {
                _state.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun updateDraft(value: String) {
        _state.update { it.copy(draft = value) }
    }

    fun send() {
        val conversationId = _state.value.conversation?.id ?: return
        val body = _state.value.draft.trim()
        if (body.isBlank()) return

        viewModelScope.launch {
            _state.update { it.copy(isSending = true, error = null) }
            try {
                val message = messagingRepository.sendMessage(conversationId, body)
                _state.update {
                    it.copy(
                        messages = it.messages + message,
                        draft = "",
                        isSending = false,
                    )
                }
            } catch (e: ApiException) {
                _state.update { it.copy(isSending = false, error = e.message) }
            }
        }
    }
}
