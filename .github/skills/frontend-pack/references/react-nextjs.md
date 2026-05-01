---
name: react-nextjs
description: 'React 18/19 + Next.js App Router patterns: server/client components, Suspense, state, forms, auth, TanStack Query, and tests.'
---
# React / Next.js Code Patterns

## Server vs Client Components

```tsx
// BAD: 'use client' on a component that only renders data
'use client';
import { useEffect, useState } from 'react';

export function PaymentList() {
  const [payments, setPayments] = useState([]);
  useEffect(() => {
    fetch('/api/payments').then(r => r.json()).then(setPayments);
  }, []);
  return <ul>{payments.map(p => <li key={p.id}>{p.amount}</li>)}</ul>;
}

// GOOD: Server component — no client JS, data fetched at build/request time
import { getPayments } from '@/lib/api';

export default async function PaymentList() {
  const payments = await getPayments();
  return (
    <ul>
      {payments.map((p) => (
        <li key={p.id}>
          {p.currency} {p.amount} — {p.status}
        </li>
      ))}
    </ul>
  );
}
```

## Client Component (Interactive)

```tsx
'use client';

import { useState, useTransition } from 'react';
import { capturePayment } from '@/app/actions/payment';

interface CaptureButtonProps {
  paymentId: string;
}

export function CaptureButton({ paymentId }: CaptureButtonProps) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleCapture() {
    setError(null);
    startTransition(async () => {
      const result = await capturePayment(paymentId);
      if (result.error) setError(result.error);
    });
  }

  return (
    <>
      <button onClick={handleCapture} disabled={isPending} aria-busy={isPending}>
        {isPending ? 'Capturing…' : 'Capture Payment'}
      </button>
      {error && <p role="alert" className="text-red-600">{error}</p>}
    </>
  );
}
```

## Suspense + Error Boundary

```tsx
import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import PaymentList from './PaymentList';
import { PaymentListSkeleton } from './PaymentListSkeleton';

export default function PaymentsPage() {
  return (
    <ErrorBoundary fallback={<p>Something went wrong loading payments.</p>}>
      <Suspense fallback={<PaymentListSkeleton />}>
        <PaymentList />
      </Suspense>
    </ErrorBoundary>
  );
}
```

## State Management Ladder

```tsx
// 1. Local state — simple UI state
const [isOpen, setIsOpen] = useState(false);

// 2. URL state — shareable, bookmarkable filters
import { useSearchParams } from 'next/navigation';

function useFilters() {
  const searchParams = useSearchParams();
  return {
    status: searchParams.get('status') ?? 'all',
    page: Number(searchParams.get('page') ?? '1'),
  };
}

// 3. Server state — TanStack Query for async data
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

function usePayments(filters: { status: string; page: number }) {
  return useQuery({
    queryKey: ['payments', filters],
    queryFn: () => fetchPayments(filters),
    staleTime: 30_000,
  });
}

function useCapturePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => capturePayment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] });
    },
  });
}

// 4. Global client state — Zustand (only when truly global)
import { create } from 'zustand';

interface NotificationStore {
  messages: string[];
  add: (msg: string) => void;
  dismiss: (index: number) => void;
}

const useNotifications = create<NotificationStore>((set) => ({
  messages: [],
  add: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  dismiss: (i) => set((s) => ({ messages: s.messages.filter((_, idx) => idx !== i) })),
}));
```

## Forms: react-hook-form + zod

```tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const PaymentSchema = z.object({
  amount: z.coerce.number().positive('Amount must be positive'),
  currency: z.string().length(3, 'Currency must be 3 characters'),
  sourceAccount: z.string().min(1, 'Required'),
  destAccount: z.string().min(1, 'Required'),
});

type PaymentFormData = z.infer<typeof PaymentSchema>;

export function PaymentForm({ onSubmit }: { onSubmit: (data: PaymentFormData) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PaymentFormData>({
    resolver: zodResolver(PaymentSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div>
        <label htmlFor="amount">Amount</label>
        <input id="amount" type="number" step="0.01" {...register('amount')} aria-invalid={!!errors.amount} />
        {errors.amount && <p role="alert">{errors.amount.message}</p>}
      </div>

      <div>
        <label htmlFor="currency">Currency</label>
        <input id="currency" maxLength={3} {...register('currency')} aria-invalid={!!errors.currency} />
        {errors.currency && <p role="alert">{errors.currency.message}</p>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting…' : 'Create Payment'}
      </button>
    </form>
  );
}
```

## Auth: httpOnly Cookies + Token Refresh

```tsx
// BAD: Token in localStorage — XSS can steal it
localStorage.setItem('token', response.token);

// GOOD: httpOnly cookie set by server, refresh via API route
// app/api/auth/login/route.ts (Next.js Route Handler)
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const { email, password } = await request.json();
  const { accessToken, refreshToken } = await authService.login(email, password);

  const cookieStore = await cookies();
  cookieStore.set('access_token', accessToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 900, // 15 minutes
    path: '/',
  });
  cookieStore.set('refresh_token', refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 604800, // 7 days
    path: '/api/auth/refresh',
  });

  return NextResponse.json({ success: true });
}
```

## Next.js Server Actions

```tsx
// app/actions/payment.ts
'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const CaptureSchema = z.object({ paymentId: z.string().uuid() });

export async function capturePayment(paymentId: string) {
  const parsed = CaptureSchema.safeParse({ paymentId });
  if (!parsed.success) {
    return { error: 'Invalid payment ID' };
  }

  try {
    await paymentService.capture(parsed.data.paymentId);
    revalidatePath('/payments');
    return { success: true };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Capture failed' };
  }
}
```

## Test: Vitest + Testing Library + MSW

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PaymentForm } from './PaymentForm';

const server = setupServer(
  http.post('/api/payments', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { id: 'pay-1', status: 'PENDING', ...body },
      { status: 201 }
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('PaymentForm', () => {
  it('submits valid form data', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithProviders(<PaymentForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('Amount'), '100');
    await user.type(screen.getByLabelText('Currency'), 'VND');
    await user.click(screen.getByRole('button', { name: /create payment/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  });

  it('shows validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<PaymentForm onSubmit={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /create payment/i }));

    expect(await screen.findByText(/amount must be positive/i)).toBeInTheDocument();
  });
});
```

## Anti-Patterns

- **useEffect for derived state**: Computing values in useEffect that can be calculated during render.
- **localStorage for tokens**: XSS can steal tokens — use httpOnly cookies.
- `useEffect` + `setState` for data fetching — use TanStack Query or server components.
- Prop drilling through 5+ levels — use context or composition (children pattern).
- `key={Math.random()}` — forces remount on every render, destroys state.
- Fetching in `useEffect` without cleanup — race conditions on fast navigation.
- `'use client'` on every component — defeats server component benefits.

## Gotchas

- Server components cannot use hooks (`useState`, `useEffect`) — split into server + client.
- `cookies()` and `headers()` in Next.js 15 are async — must `await`.
- `revalidatePath` only works in server actions and route handlers.
- TanStack Query `staleTime` defaults to 0 — set explicitly to avoid refetch storms.
- `useSearchParams()` requires `<Suspense>` boundary in Next.js App Router.
- `next/image` requires explicit `width`/`height` or `fill` — no auto-sizing.
- React 19 `use()` hook can read promises and context — but only in client components.
