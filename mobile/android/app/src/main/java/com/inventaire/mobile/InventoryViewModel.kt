package com.inventaire.mobile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.inventaire.mobile.data.AuthSession
import com.inventaire.mobile.data.AuthenticationException
import com.inventaire.mobile.data.InventoryRepository
import com.inventaire.mobile.data.Product
import com.inventaire.mobile.data.RemoteDataException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class InventoryViewModel(
    private val repository: InventoryRepository = InventoryRepository(),
) : ViewModel() {

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    fun login(username: String, password: String) {
        val trimmedUsername = username.trim()
        if (trimmedUsername.isEmpty() || password.isEmpty()) {
            _uiState.update { it.copy(errorMessage = "Identifiant et mot de passe requis") }
            return
        }
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            try {
                val session = repository.login(trimmedUsername, password)
                val products = repository.loadProducts(session.token)
                _uiState.value = UiState(
                    session = session,
                    products = products,
                    isLoading = false,
                    errorMessage = null,
                )
            } catch (exception: AuthenticationException) {
                _uiState.update { it.copy(isLoading = false, errorMessage = exception.message) }
            } catch (exception: RemoteDataException) {
                _uiState.update { it.copy(isLoading = false, session = null, errorMessage = exception.message) }
            } catch (exception: Exception) {
                _uiState.update { it.copy(isLoading = false, errorMessage = "Erreur inattendue : ${exception.message}") }
            }
        }
    }

    fun refreshInventory() {
        val session = _uiState.value.session ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            try {
                val products = repository.loadProducts(session.token)
                _uiState.update { it.copy(products = products, isLoading = false) }
            } catch (exception: RemoteDataException) {
                _uiState.update { it.copy(isLoading = false, errorMessage = exception.message) }
            } catch (exception: Exception) {
                _uiState.update { it.copy(isLoading = false, errorMessage = "Erreur inattendue : ${exception.message}") }
            }
        }
    }

    fun logout() {
        _uiState.value = UiState()
    }

    fun clearError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    data class UiState(
        val session: AuthSession? = null,
        val products: List<Product> = emptyList(),
        val isLoading: Boolean = false,
        val errorMessage: String? = null,
    )
}
