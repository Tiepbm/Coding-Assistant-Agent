---
name: mobile-pack
description: 'Use when building mobile apps: React Native, Flutter, native iOS (Swift/SwiftUI), or native Android (Kotlin/Compose). Components, navigation, permissions, offline support, secure storage, platform-specific code.'
---
# Mobile Pack

## When to Use
- Cross-platform: React Native or Flutter components, navigation, state.
- Native iOS: SwiftUI views, Observable state, URLSession, Keychain.
- Native Android: Jetpack Compose, ViewModel + StateFlow, Hilt, Retrofit.
- Device permissions (camera, location, notifications) per platform.
- Offline-first patterns (queue, sync, conflict resolution).
- Secure storage (Keychain/Keystore/EncryptedSharedPreferences — NOT UserDefaults/SharedPrefs/AsyncStorage for secrets).
- Platform-specific code or differences (iOS vs Android).

## When NOT to Use
- Web React/Vue/Angular components → `frontend-pack`.
- Backend API that mobile app calls → `backend-pack`.
- Mobile CI/CD pipeline (Fastlane, EAS, Bitrise) → `devops-pack`.
- Mobile E2E tests (Detox/Maestro/XCUITest/Espresso) → `testing-pack/e2e-testing`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `react-native` | React Native + Expo: components, navigation, secure storage, offline, platform code, Jest tests. |
| `flutter` | Flutter widgets, Riverpod state, go_router, Dio, secure storage, widget tests. |
| `swift-ios` | Native iOS SwiftUI, Observable, URLSession async/await, Keychain, XCTest. |
| `kotlin-android` | Native Android Jetpack Compose, ViewModel + StateFlow, Hilt, Retrofit, EncryptedSharedPreferences, Compose tests. |

## Cross-Pack Handoffs
- → `backend-pack` for API endpoints the mobile app consumes.
- → `testing-pack` for Detox/Maestro E2E tests and Jest unit tests.
- → `frontend-pack` when sharing code between web and mobile (shared hooks, types).
- → `quality-pack` for mobile code review and accessibility.
- → `devops-pack` for mobile CI/CD (EAS Build, Fastlane).
