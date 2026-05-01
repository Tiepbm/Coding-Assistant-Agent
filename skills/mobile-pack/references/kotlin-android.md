---
name: kotlin-android
description: 'Native Android Kotlin patterns: Jetpack Compose, ViewModel + StateFlow, Hilt, Retrofit, EncryptedSharedPreferences, Compose tests.'
---
# Kotlin / Android Code Patterns

## Compose Screen Pattern

```kotlin
// BAD: Logic in composable, hardcoded strings, no state hoisting
@Composable
fun PaymentList() {
    val payments = remember { fetchPayments() } // network in composition!
    Column { payments.forEach { Text(it.toString()) } }
}

// GOOD: State hoisted, ViewModel-driven, accessible
@Composable
fun PaymentListScreen(viewModel: PaymentListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    PaymentListContent(state = state, onRetry = viewModel::load, onTap = viewModel::open)
}

@Composable
fun PaymentListContent(
    state: PaymentListState,
    onRetry: () -> Unit,
    onTap: (PaymentId) -> Unit,
) {
    when (state) {
        is PaymentListState.Loading -> CircularProgressIndicator(
            Modifier.semantics { contentDescription = "Loading payments" }
        )
        is PaymentListState.Error   -> ErrorView(state.message, onRetry)
        is PaymentListState.Loaded  -> LazyColumn {
            items(state.payments, key = { it.id.value }) { p ->
                PaymentCard(payment = p, onTap = onTap)
            }
        }
    }
}
```

## ViewModel + StateFlow

```kotlin
@HiltViewModel
class PaymentListViewModel @Inject constructor(
    private val repository: PaymentRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<PaymentListState>(PaymentListState.Loading)
    val state: StateFlow<PaymentListState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = PaymentListState.Loading
            _state.value = runCatching { repository.list() }
                .fold(
                    onSuccess = { PaymentListState.Loaded(it) },
                    onFailure = { PaymentListState.Error(it.message ?: "unknown") },
                )
        }
    }
}

sealed interface PaymentListState {
    data object Loading : PaymentListState
    data class Loaded(val payments: List<Payment>) : PaymentListState
    data class Error(val message: String) : PaymentListState
}
```

## Repository + Retrofit + Result

```kotlin
interface PaymentApi {
    @GET("payments") suspend fun list(): List<PaymentDto>
    @POST("payments") suspend fun create(@Body req: CreatePaymentRequest): PaymentDto
}

class PaymentRepository @Inject constructor(
    private val api: PaymentApi,
    private val dispatcher: CoroutineDispatcher,  // inject for testability
) {
    suspend fun list(): List<Payment> = withContext(dispatcher) {
        api.list().map { it.toDomain() }
    }
}
```

## Secure Storage (EncryptedSharedPreferences — NOT regular SharedPrefs for tokens)

```kotlin
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

val prefs = EncryptedSharedPreferences.create(
    context, "auth", masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
)
prefs.edit().putString("access_token", token).apply()
```

## Test (Compose + Turbine)

```kotlin
@Test
fun `load emits Loading then Loaded`() = runTest {
    val api = FakePaymentApi(listOf(samplePaymentDto()))
    val vm = PaymentListViewModel(PaymentRepository(api, UnconfinedTestDispatcher()))

    vm.state.test {
        assertEquals(PaymentListState.Loading, awaitItem())
        val loaded = awaitItem() as PaymentListState.Loaded
        assertEquals(1, loaded.payments.size)
    }
}

@Test
fun paymentList_showsItems() {
    composeTestRule.setContent {
        PaymentListContent(PaymentListState.Loaded(listOf(samplePayment())), {}, {})
    }
    composeTestRule.onNodeWithText("VND 100").assertIsDisplayed()
}
```

## Verification

```bash
./gradlew testDebugUnitTest connectedDebugAndroidTest
./gradlew detekt ktlintCheck
./gradlew lintDebug
```

