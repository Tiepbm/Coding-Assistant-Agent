---
name: flutter
description: 'Flutter patterns: widgets, Riverpod state, go_router, Dio + Retrofit, secure storage, widget tests.'
---
# Flutter Code Patterns

## Widget Pattern (Stateless + typed)

```dart
// BAD: Logic in build, no const, magic strings
class PaymentCard extends StatelessWidget {
  final dynamic payment;
  PaymentCard(this.payment);
  Widget build(c) => Container(child: Text("\${payment['amount']}"));
}

// GOOD: Typed, const, accessible
class PaymentCard extends StatelessWidget {
  const PaymentCard({super.key, required this.payment, required this.onTap});
  final Payment payment;
  final void Function(String id) onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Payment \${payment.amount} \${payment.currency}, status \${payment.status}',
      child: InkWell(
        onTap: () => onTap(payment.id),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(children: [
            Text('\${payment.currency} \${payment.amount}',
              style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            StatusBadge(status: payment.status),
          ]),
        ),
      ),
    );
  }
}
```

## State Management (Riverpod 2)

```dart
@riverpod
class PaymentList extends _$PaymentList {
  @override
  Future<List<Payment>> build() async {
    final api = ref.watch(paymentApiProvider);
    return api.list();
  }

  Future<void> create(CreatePaymentRequest req) async {
    final api = ref.read(paymentApiProvider);
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await api.create(req);
      return api.list();
    });
  }
}

// Usage
final asyncPayments = ref.watch(paymentListProvider);
asyncPayments.when(
  loading: () => const CircularProgressIndicator(),
  error: (e, _) => ErrorView(error: e),
  data: (payments) => ListView(children: payments.map(...).toList()),
);
```

## Routing (go_router)

```dart
final router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
    GoRoute(
      path: '/payments/:id',
      builder: (_, state) => PaymentDetailScreen(id: state.pathParameters['id']!),
    ),
  ],
  redirect: (context, state) {
    final loggedIn = ref.read(authProvider).isAuthenticated;
    return loggedIn ? null : '/login';
  },
);
```

## API Client (Dio + interceptor)

```dart
final dio = Dio(BaseOptions(
  baseUrl: 'https://api.example.com',
  connectTimeout: const Duration(seconds: 5),
  receiveTimeout: const Duration(seconds: 10),
))..interceptors.addAll([
    AuthInterceptor(tokenStorage),
    RetryInterceptor(retries: 3, retryableStatuses: {502, 503, 504}),
    LogInterceptor(logPrint: log.fine),
  ]);
```

## Secure Storage (NEVER SharedPreferences for tokens)

```dart
const storage = FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
  iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
);
await storage.write(key: 'access_token', value: token);
```

## Widget Test

```dart
testWidgets('PaymentCard shows amount and triggers onTap', (tester) async {
  String? tapped;
  await tester.pumpWidget(MaterialApp(home: PaymentCard(
    payment: Payment(id: 'p1', amount: 100, currency: 'VND', status: 'PENDING'),
    onTap: (id) => tapped = id,
  )));
  expect(find.text('VND 100'), findsOneWidget);
  await tester.tap(find.byType(InkWell));
  expect(tapped, 'p1');
});
```

## Verification

```bash
flutter test --coverage
flutter analyze
dart format --set-exit-if-changed .
```

