---
name: react-native
description: 'React Native + Expo patterns: components, navigation, secure storage, offline queue, platform differences, and tests.'
---
# React Native Code Patterns

## Component Pattern

```tsx
// BAD: Inline styles, no TypeScript, no accessibility
const PaymentCard = ({ payment }) => (
  <View style={{ padding: 16, backgroundColor: '#fff', marginBottom: 8 }}>
    <Text style={{ fontSize: 18 }}>{payment.amount}</Text>
    <Text>{payment.status}</Text>
  </View>
);

// GOOD: Typed props, StyleSheet, accessible
import { View, Text, StyleSheet, Pressable } from 'react-native';

interface PaymentCardProps {
  payment: Payment;
  onPress: (id: string) => void;
}

export function PaymentCard({ payment, onPress }: PaymentCardProps) {
  return (
    <Pressable
      onPress={() => onPress(payment.id)}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Payment ${payment.amount} ${payment.currency}, status ${payment.status}`}
    >
      <View style={styles.row}>
        <Text style={styles.amount}>
          {payment.currency} {payment.amount}
        </Text>
        <StatusBadge status={payment.status} />
      </View>
      <Text style={styles.date}>
        {new Date(payment.createdAt).toLocaleDateString()}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2, // Android shadow
  },
  cardPressed: { opacity: 0.7 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  amount: { fontSize: 18, fontWeight: '600' },
  date: { fontSize: 14, color: '#666', marginTop: 4 },
});
```

## Navigation (React Navigation + Typed Params)

```tsx
// BAD: Untyped navigation — runtime crashes on wrong params
navigation.navigate('PaymentDetail', { id: payment.id });
// If PaymentDetail expects 'paymentId' instead of 'id' → crash

// GOOD: Typed navigation with RootStackParamList
import { NativeStackScreenProps } from '@react-navigation/native-stack';

// Define all routes and their params
type RootStackParamList = {
  PaymentList: undefined;
  PaymentDetail: { paymentId: string };
  CreatePayment: { tenantId: string };
};

// Typed screen props
type PaymentDetailProps = NativeStackScreenProps<RootStackParamList, 'PaymentDetail'>;

export function PaymentDetailScreen({ route, navigation }: PaymentDetailProps) {
  const { paymentId } = route.params; // Type-safe

  return (
    <View>
      <Text>Payment: {paymentId}</Text>
      <Button
        title="Back to List"
        onPress={() => navigation.navigate('PaymentList')}
      />
    </View>
  );
}

// Navigator setup
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="PaymentList" component={PaymentListScreen} />
      <Stack.Screen name="PaymentDetail" component={PaymentDetailScreen} />
      <Stack.Screen name="CreatePayment" component={CreatePaymentScreen} />
    </Stack.Navigator>
  );
}
```

## Secure Storage

```tsx
// BAD: AsyncStorage for tokens — unencrypted, accessible to other apps on rooted devices
import AsyncStorage from '@react-native-async-storage/async-storage';
await AsyncStorage.setItem('accessToken', token); // ❌ NOT SECURE

// GOOD: expo-secure-store (Keychain on iOS, Keystore on Android)
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export const secureStorage = {
  async saveTokens(access: string, refresh: string): Promise<void> {
    await SecureStore.setItemAsync(TOKEN_KEY, access, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
    await SecureStore.setItemAsync(REFRESH_KEY, refresh, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },

  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync(TOKEN_KEY);
  },

  async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync(REFRESH_KEY);
  },

  async clearTokens(): Promise<void> {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
```

## Offline Queue with Idempotency

```tsx
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { v4 as uuidv4 } from 'uuid';

interface QueuedAction {
  id: string;           // Idempotency key
  endpoint: string;
  method: 'POST' | 'PUT' | 'DELETE';
  body: unknown;
  createdAt: string;
  retryCount: number;
}

const QUEUE_KEY = 'offline_queue';

export class OfflineQueue {
  async enqueue(action: Omit<QueuedAction, 'id' | 'createdAt' | 'retryCount'>): Promise<string> {
    const id = uuidv4();
    const queued: QueuedAction = {
      ...action,
      id,
      createdAt: new Date().toISOString(),
      retryCount: 0,
    };

    const existing = await this.getQueue();
    existing.push(queued);
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(existing));
    return id;
  }

  async processQueue(): Promise<void> {
    const state = await NetInfo.fetch();
    if (!state.isConnected) return;

    const queue = await this.getQueue();
    const remaining: QueuedAction[] = [];

    for (const action of queue) {
      try {
        await fetch(action.endpoint, {
          method: action.method,
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': action.id, // Server deduplicates
          },
          body: JSON.stringify(action.body),
        });
        // Success — don't add back to queue
      } catch {
        if (action.retryCount < 3) {
          remaining.push({ ...action, retryCount: action.retryCount + 1 });
        }
        // Drop after 3 retries
      }
    }

    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
  }

  private async getQueue(): Promise<QueuedAction[]> {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  }
}

// Usage: Listen for connectivity changes
NetInfo.addEventListener((state) => {
  if (state.isConnected) {
    offlineQueue.processQueue();
  }
});
```

## Platform Differences

```tsx
import { Platform, StyleSheet } from 'react-native';

// Platform-specific styles
const styles = StyleSheet.create({
  shadow: Platform.select({
    ios: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
    },
    android: {
      elevation: 4,
    },
    default: {},
  }),
});

// Platform-specific file (auto-resolved by bundler)
// components/DatePicker.ios.tsx  — iOS implementation
// components/DatePicker.android.tsx — Android implementation
// components/DatePicker.tsx — fallback/web

// Platform-specific permissions
import * as ImagePicker from 'expo-image-picker';

async function requestCameraPermission(): Promise<boolean> {
  if (Platform.OS === 'web') return true;

  const { status } = await ImagePicker.requestCameraPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert(
      'Permission Required',
      'Camera access is needed to scan documents.',
      [{ text: 'Open Settings', onPress: () => Linking.openSettings() }]
    );
    return false;
  }
  return true;
}
```

## API Client with Auth Refresh

```tsx
import { secureStorage } from './secure-storage';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async fetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = await secureStorage.getAccessToken();

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    // Token expired — try refresh
    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        return this.fetch<T>(path, options); // Retry with new token
      }
      throw new AuthError('Session expired');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.message ?? 'Request failed');
    }

    return response.json();
  }

  private async refreshToken(): Promise<boolean> {
    const refreshToken = await secureStorage.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });

      if (!response.ok) return false;

      const { accessToken, refreshToken: newRefresh } = await response.json();
      await secureStorage.saveTokens(accessToken, newRefresh);
      return true;
    } catch {
      return false;
    }
  }
}
```

## Test: Jest + Testing Library

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { PaymentCard } from './PaymentCard';

describe('PaymentCard', () => {
  const mockPayment: Payment = {
    id: 'pay-1',
    amount: '100.00',
    currency: 'VND',
    status: 'PENDING',
    createdAt: '2024-01-15T10:00:00Z',
  };

  it('renders payment details', () => {
    const onPress = jest.fn();
    render(<PaymentCard payment={mockPayment} onPress={onPress} />);

    expect(screen.getByText('VND 100.00')).toBeTruthy();
    expect(screen.getByText('PENDING')).toBeTruthy();
  });

  it('calls onPress with payment id', () => {
    const onPress = jest.fn();
    render(<PaymentCard payment={mockPayment} onPress={onPress} />);

    fireEvent.press(screen.getByRole('button'));

    expect(onPress).toHaveBeenCalledWith('pay-1');
  });

  it('has accessible label', () => {
    render(<PaymentCard payment={mockPayment} onPress={jest.fn()} />);

    expect(screen.getByLabelText(/payment 100.00 vnd/i)).toBeTruthy();
  });
});
```

## Anti-Patterns

- **AsyncStorage for secrets**: Unencrypted, accessible on rooted/jailbroken devices.
- **Large navigation params**: Passing full objects — use IDs and fetch in the screen.
- `console.log` in production — use a proper logger with log levels.
- Inline styles everywhere — use `StyleSheet.create` for performance.
- Ignoring keyboard avoidance — forms hidden behind keyboard on small screens.
- Synchronous heavy computation on JS thread — use `InteractionManager` or native modules.
- Hardcoded API URLs — use environment config (expo-constants, react-native-config).

## Gotchas

- `SecureStore` has a 2048-byte limit per item — don't store large payloads.
- `AsyncStorage` is async but NOT encrypted — fine for preferences, not for tokens.
- React Navigation `navigate` vs `push`: `navigate` reuses existing screen, `push` adds new.
- `FlatList` `keyExtractor` must return a string — not a number.
- iOS requires `NSCameraUsageDescription` in Info.plist for camera access.
- Android 13+ requires `POST_NOTIFICATIONS` permission for push notifications.
- Expo Go has limitations — some native modules require a development build.
