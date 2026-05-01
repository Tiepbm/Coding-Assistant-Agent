---
name: swift-ios
description: 'Native iOS Swift patterns: SwiftUI views, async/await, observable state, Keychain, URLSession, XCTest.'
---
# Swift / iOS Code Patterns

## SwiftUI View Pattern

```swift
// BAD: View with side-effects in body, no preview, untyped
struct PaymentCard: View {
    var payment: [String: Any]
    var body: some View { Text("\(payment["amount"]!)") }
}

// GOOD: Typed model, accessible, previewable
struct PaymentCard: View {
    let payment: Payment
    let onTap: (UUID) -> Void

    var body: some View {
        Button(action: { onTap(payment.id) }) {
            HStack {
                Text("\(payment.currency) \(payment.amount.formatted())")
                    .font(.headline)
                Spacer()
                StatusBadge(status: payment.status)
            }
            .padding()
        }
        .accessibilityLabel("Payment \(payment.amount) \(payment.currency), status \(payment.status.rawValue)")
        .accessibilityAddTraits(.isButton)
    }
}

#Preview { PaymentCard(payment: .sample, onTap: { _ in }) }
```

## State (Observable, iOS 17+)

```swift
@Observable
final class PaymentListViewModel {
    private(set) var payments: [Payment] = []
    private(set) var state: LoadState = .idle

    enum LoadState { case idle, loading, loaded, failed(Error) }

    private let api: PaymentAPI
    init(api: PaymentAPI) { self.api = api }

    func load() async {
        state = .loading
        do {
            payments = try await api.list()
            state = .loaded
        } catch { state = .failed(error) }
    }
}

struct PaymentListView: View {
    @State private var vm: PaymentListViewModel
    var body: some View {
        Group {
            switch vm.state {
            case .loading: ProgressView()
            case .failed(let e): ErrorView(error: e, retry: { Task { await vm.load() } })
            default: List(vm.payments) { PaymentCard(payment: $0, onTap: { _ in }) }
            }
        }
        .task { await vm.load() }
    }
}
```

## Networking (URLSession + async/await)

```swift
struct PaymentAPI {
    let session: URLSession
    let baseURL: URL

    func create(_ req: CreatePaymentRequest) async throws -> Payment {
        var request = URLRequest(url: baseURL.appending(path: "payments"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.iso8601.encode(req)
        request.timeoutInterval = 10

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        switch http.statusCode {
        case 200...299: return try JSONDecoder.iso8601.decode(Payment.self, from: data)
        case 409:       throw APIError.idempotencyConflict
        case 400...499: throw APIError.client(http.statusCode)
        default:        throw APIError.server(http.statusCode)
        }
    }
}
```

## Secure Storage (Keychain — NEVER UserDefaults for tokens)

```swift
enum Keychain {
    static func save(_ value: String, key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: Data(value.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        SecItemDelete(query as CFDictionary)
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.unhandled(status) }
    }
}
```

## Test (XCTest async)

```swift
final class PaymentListViewModelTests: XCTestCase {
    @MainActor
    func test_load_setsLoadedStateOnSuccess() async {
        let api = MockPaymentAPI(payments: [.sample])
        let vm = PaymentListViewModel(api: api)
        await vm.load()
        XCTAssertEqual(vm.payments.count, 1)
        if case .loaded = vm.state { } else { XCTFail("expected .loaded") }
    }
}
```

## Verification

```bash
xcodebuild test -scheme App -destination 'platform=iOS Simulator,name=iPhone 15' -enableCodeCoverage YES
swiftlint --strict
```

