---
name: vue-nuxt
description: 'Vue 3 Composition API + Nuxt 3 patterns: composables, Pinia, forms, SSR/SSG, useFetch, auto-imports, and tests.'
---
# Vue / Nuxt Code Patterns

## Composition API Component

```vue
<!-- BAD: Options API in new code — verbose, poor TypeScript support -->
<script>
export default {
  data() {
    return { payments: [], loading: true };
  },
  async mounted() {
    this.payments = await fetch('/api/payments').then(r => r.json());
    this.loading = false;
  },
};
</script>

<!-- GOOD: Composition API with script setup -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { Payment } from '~/types/payment';

const payments = ref<Payment[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

const totalAmount = computed(() =>
  payments.value.reduce((sum, p) => sum + Number(p.amount), 0)
);

onMounted(async () => {
  try {
    const response = await $fetch<Payment[]>('/api/payments');
    payments.value = response;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <ul v-else>
      <li v-for="payment in payments" :key="payment.id">
        {{ payment.currency }} {{ payment.amount }} — {{ payment.status }}
      </li>
    </ul>
    <p>Total: {{ totalAmount }}</p>
  </div>
</template>
```

## Composables

```typescript
// BAD: Duplicating fetch logic in every component
// GOOD: Extract reusable composable
// composables/usePayments.ts
import type { Payment } from '~/types/payment';

export function usePayments() {
  const payments = ref<Payment[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchPayments(filters?: { status?: string }) {
    loading.value = true;
    error.value = null;
    try {
      payments.value = await $fetch<Payment[]>('/api/payments', {
        query: filters,
      });
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Fetch failed';
    } finally {
      loading.value = false;
    }
  }

  async function capturePayment(id: string) {
    await $fetch(`/api/payments/${id}/capture`, { method: 'POST' });
    // Refresh list
    await fetchPayments();
  }

  return { payments, loading, error, fetchPayments, capturePayment };
}
```

## Pinia State Management

```typescript
// BAD: Vuex with mutations, actions, getters boilerplate
// GOOD: Pinia setup store — clean, typed, composable
// stores/payment.ts
import { defineStore } from 'pinia';
import type { Payment } from '~/types/payment';

export const usePaymentStore = defineStore('payment', () => {
  const payments = ref<Payment[]>([]);
  const loading = ref(false);

  const pendingPayments = computed(() =>
    payments.value.filter((p) => p.status === 'PENDING')
  );

  async function load() {
    loading.value = true;
    try {
      payments.value = await $fetch<Payment[]>('/api/payments');
    } finally {
      loading.value = false;
    }
  }

  async function capture(id: string) {
    await $fetch(`/api/payments/${id}/capture`, { method: 'POST' });
    const payment = payments.value.find((p) => p.id === id);
    if (payment) payment.status = 'CAPTURED'; // Optimistic update
  }

  return { payments, loading, pendingPayments, load, capture };
});
```

## Nuxt 3: useFetch / useAsyncData

```vue
<!-- BAD: Manual fetch in onMounted — no SSR, no caching -->
<script setup>
const data = ref(null);
onMounted(async () => { data.value = await fetch('/api/payments').then(r => r.json()); });
</script>

<!-- GOOD: useFetch — SSR-compatible, cached, auto-refreshable -->
<script setup lang="ts">
import type { Payment } from '~/types/payment';

const route = useRoute();

const { data: payments, status, error, refresh } = await useFetch<Payment[]>(
  '/api/payments',
  {
    query: { status: route.query.status },
    watch: [() => route.query.status], // Re-fetch when filter changes
  }
);
</script>

<template>
  <div>
    <button @click="refresh()">Refresh</button>
    <p v-if="status === 'pending'">Loading…</p>
    <p v-else-if="error" role="alert">{{ error.message }}</p>
    <PaymentList v-else :payments="payments ?? []" />
  </div>
</template>
```

## Nuxt Server Routes (API)

```typescript
// server/api/payments/index.post.ts
import { z } from 'zod';

const CreatePaymentSchema = z.object({
  tenantId: z.string().uuid(),
  amount: z.number().positive(),
  currency: z.string().length(3),
});

export default defineEventHandler(async (event) => {
  const body = await readValidatedBody(event, CreatePaymentSchema.parse);

  const payment = await prisma.payment.create({
    data: {
      tenantId: body.tenantId,
      amount: body.amount,
      currency: body.currency,
      status: 'PENDING',
    },
  });

  setResponseStatus(event, 201);
  return payment;
});
```

## Forms: VeeValidate + Zod

```vue
<script setup lang="ts">
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';
import { z } from 'zod';

const schema = toTypedSchema(
  z.object({
    amount: z.number({ coerce: true }).positive('Amount must be positive'),
    currency: z.string().length(3, 'Must be 3 characters'),
    sourceAccount: z.string().min(1, 'Required'),
    destAccount: z.string().min(1, 'Required'),
  })
);

const { handleSubmit, errors, isSubmitting, defineField } = useForm({
  validationSchema: schema,
});

const [amount, amountAttrs] = defineField('amount');
const [currency, currencyAttrs] = defineField('currency');
const [sourceAccount, sourceAttrs] = defineField('sourceAccount');
const [destAccount, destAttrs] = defineField('destAccount');

const onSubmit = handleSubmit(async (values) => {
  await $fetch('/api/payments', { method: 'POST', body: values });
  navigateTo('/payments');
});
</script>

<template>
  <form @submit="onSubmit" novalidate>
    <div>
      <label for="amount">Amount</label>
      <input id="amount" type="number" v-model="amount" v-bind="amountAttrs"
             :aria-invalid="!!errors.amount" />
      <p v-if="errors.amount" role="alert">{{ errors.amount }}</p>
    </div>

    <div>
      <label for="currency">Currency</label>
      <input id="currency" v-model="currency" v-bind="currencyAttrs" maxlength="3"
             :aria-invalid="!!errors.currency" />
      <p v-if="errors.currency" role="alert">{{ errors.currency }}</p>
    </div>

    <button type="submit" :disabled="isSubmitting">
      {{ isSubmitting ? 'Submitting…' : 'Create Payment' }}
    </button>
  </form>
</template>
```

## SSR / SSG Configuration

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  // Hybrid rendering: SSR by default, static for marketing pages
  routeRules: {
    '/': { prerender: true },           // SSG — static at build time
    '/about': { prerender: true },
    '/dashboard/**': { ssr: true },     // SSR — dynamic per request
    '/api/**': { cors: true },          // API routes
  },
  runtimeConfig: {
    databaseUrl: '',                    // Server-only (from env)
    public: {
      apiBase: '/api',                  // Available on client
    },
  },
});
```

## Test: Vitest + Vue Test Utils + MSW

```typescript
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import PaymentList from './PaymentList.vue';

const server = setupServer(
  http.get('/api/payments', () => {
    return HttpResponse.json([
      { id: '1', amount: 100, currency: 'VND', status: 'PENDING' },
      { id: '2', amount: 200, currency: 'VND', status: 'CAPTURED' },
    ]);
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('PaymentList', () => {
  it('renders payment items', async () => {
    const wrapper = mount(PaymentList, {
      global: {
        plugins: [createTestingPinia({ stubActions: false })],
      },
    });

    // Wait for async data
    await vi.waitFor(() => {
      expect(wrapper.findAll('li')).toHaveLength(2);
    });

    expect(wrapper.text()).toContain('VND 100');
    expect(wrapper.text()).toContain('PENDING');
  });

  it('shows error message on fetch failure', async () => {
    server.use(
      http.get('/api/payments', () => HttpResponse.error())
    );

    const wrapper = mount(PaymentList, {
      global: {
        plugins: [createTestingPinia({ stubActions: false })],
      },
    });

    await vi.waitFor(() => {
      expect(wrapper.find('[role="alert"]').exists()).toBe(true);
    });
  });
});
```

## Anti-Patterns

- **Options API in new code**: Composition API has better TypeScript support and composability.
- **Mutating props**: `props.items.push(item)` — emit events or use Pinia instead.
- `v-if` + `v-for` on same element — `v-if` has higher priority in Vue 3, causes confusion.
- Reactive object destructuring: `const { count } = store` loses reactivity — use `storeToRefs()`.
- `watch` with `{ immediate: true, deep: true }` on large objects — performance killer.
- Global state in composables without Pinia — shared state across SSR requests (memory leak).
- `$fetch` in `onMounted` instead of `useFetch` — misses SSR, causes hydration mismatch.

## Gotchas

- `useFetch` / `useAsyncData` must be called at top level of `<script setup>` — not inside callbacks.
- Nuxt auto-imports: `ref`, `computed`, `useFetch` are available without import — but IDE needs config.
- `$fetch` in Nuxt server routes calls the handler directly (no HTTP roundtrip) during SSR.
- Pinia stores in SSR: state is shared across requests unless using `defineStore` with setup syntax.
- `storeToRefs()` required to destructure reactive properties from Pinia store.
- `navigateTo()` in Nuxt replaces `router.push()` — works in both server and client context.
- Vue 3 `<Teleport>` doesn't work during SSR — use `<ClientOnly>` wrapper.
