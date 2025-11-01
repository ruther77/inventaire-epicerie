package com.inventaire.mobile.data

import android.util.Log
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.HttpRequestRetry
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private const val TAG = "InventoryRepository"

object ApiConfig {
    const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
}

class InventoryRepository(
    private val baseUrl: String = ApiConfig.DEFAULT_BASE_URL,
    private val json: Json = Json { ignoreUnknownKeys = true }
) {
    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(json)
        }
        install(Logging) {
            level = LogLevel.INFO
            logger = object : Logger {
                override fun log(message: String) {
                    Log.d(TAG, message)
                }
            }
        }
        install(HttpRequestRetry) {
            maxRetries = 2
            retryOnServerErrors()
            exponentialDelay()
        }
    }

    suspend fun login(username: String, password: String): AuthSession {
        return try {
            val response: LoginResponse = client.post("$baseUrl/auth/login") {
                contentType(ContentType.Application.Json)
                setBody(LoginRequest(username = username, password = password))
            }.body()
            AuthSession(token = response.accessToken, user = response.user)
        } catch (exception: ClientRequestException) {
            val message = runCatching { exception.response.body<ApiError>() }.getOrNull()?.detail
            throw AuthenticationException(message ?: "Identifiants invalides", exception)
        }
    }

    suspend fun loadProducts(token: String): List<Product> {
        return try {
            client.get("$baseUrl/products") {
                header(HttpHeaders.Authorization, "Bearer $token")
            }.body()
        } catch (exception: ClientRequestException) {
            val message = runCatching { exception.response.body<ApiError>() }.getOrNull()?.detail
            throw RemoteDataException(message ?: "Impossible de récupérer les produits", exception)
        }
    }
}

class AuthenticationException(message: String, cause: Throwable? = null) : Exception(message, cause)
class RemoteDataException(message: String, cause: Throwable? = null) : Exception(message, cause)

data class AuthSession(
    val token: String,
    val user: User,
)

@Serializable
data class LoginRequest(
    val username: String,
    val password: String,
)

@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    val user: User,
)

@Serializable
data class User(
    val id: Int,
    val username: String,
    val email: String? = null,
    @SerialName("full_name") val fullName: String? = null,
    val role: String,
    @SerialName("is_active") val isActive: Boolean,
)

@Serializable
data class Product(
    val id: Int,
    val nom: String,
    val categorie: String? = null,
    @SerialName("prix_vente") val prixVente: Double,
    @SerialName("prix_achat") val prixAchat: Double? = null,
    @SerialName("stock_actuel") val stockActuel: Double? = null,
    val tva: Double? = null,
)

@Serializable
data class ApiError(
    val detail: String? = null,
)
