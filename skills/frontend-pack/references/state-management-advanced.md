---
name: state-management-advanced
description: 'Advanced client state: server-state vs client-state separation, Zustand/Jotai/Redux Toolkit, Pinia stores, Angular signals stores, normalization, optimistic updates.'
---
# Advanced State Management Patterns

## Rule 1 — Separate Server State from Client State

```tsx
// BAD: Storing API data in Redux/Zustand → re-implements caching, staleness, refetch manually
const useStore = create((set) => ({
  payments: [],
  loadPayments: async () => set({ payments: await api.list() }),
}));

// GOOD: Server state → TanStack Query / SWR; client-only state → Zustand/Jotai/signals
const { data: payments } = useQuery({ queryKey: ['payments'], queryFn: api.list });
const filter = useUIStore((s) => s.filter); // client-only UI state
```

## Zustand (slice + selector pattern)

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface CartState {
  items: Record<string, CartItem>;
  add: (item: CartItem) => void;
  remove: (id: string) => void;
  clear: () => void;
}

export const useCart = create<CartState>()(
  devtools(persist((set) => ({
    items: {},
    add: (item) => set((s) => ({ items: { ...s.items, [item.id]: item } })),
    remove: (id) => set((s) => {
      const { [id]: _, ...rest } = s.items;
      return { items: rest };
    }),
    clear: () => set({ items: {} }),
  }), { name: 'cart' }))
);

// Selector — only re-render when count changes
const itemCount = useCart((s) => Object.keys(s.items).length);
```

## Jotai (atom composition)

```typescript
import { atom, useAtom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

const filterAtom = atom('all');
const paymentsAtom = atom<Payment[]>([]);
const filteredAtom = atom((get) => {
  const f = get(filterAtom);
  return get(paymentsAtom).filter(p => f === 'all' || p.status === f);
});

const tokenAtom = atomWithStorage('access_token', null);
```

## Redux Toolkit + RTK Query

```typescript
export const paymentsApi = createApi({
  reducerPath: 'paymentsApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api', prepareHeaders: (h) => {
    const t = tokenStorage.get();
    if (t) h.set('authorization', `Bearer ${t}`);
    return h;
  }}),
  tagTypes: ['Payment'],
  endpoints: (b) => ({
    list:   b.query<Payment[], void>({ query: () => 'payments', providesTags: ['Payment'] }),
    create: b.mutation<Payment, CreatePaymentRequest>({
      query: (body) => ({ url: 'payments', method: 'POST', body }),
      invalidatesTags: ['Payment'],
    }),
  }),
});
```

## Optimistic Updates (TanStack Query)

```tsx
const mutation = useMutation({
  mutationFn: api.create,
  onMutate: async (newPayment) => {
    await queryClient.cancelQueries({ queryKey: ['payments'] });
    const previous = queryClient.getQueryData<Payment[]>(['payments']);
    queryClient.setQueryData<Payment[]>(['payments'], (old = []) => [
      { ...newPayment, id: 'temp-' + crypto.randomUUID(), status: 'PENDING' },
      ...old,
    ]);
    return { previous };
  },
  onError: (_err, _new, ctx) => {
    queryClient.setQueryData(['payments'], ctx?.previous); // rollback
    toast.error('Create failed');
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['payments'] }),
});
```

## Pinia (Vue) — setup syntax

```typescript
export const usePaymentStore = defineStore('payment', () => {
  const filter = ref<'all' | 'pending' | 'paid'>('all');
  const payments = ref<Payment[]>([]);
  const filtered = computed(() => filter.value === 'all'
    ? payments.value
    : payments.value.filter(p => p.status === filter.value));

  async function load() { payments.value = await paymentApi.list(); }
  return { filter, payments, filtered, load };
});
```

## Angular — Signal Store (NgRx Signals)

```typescript
export const PaymentStore = signalStore(
  withState({ payments: [] as Payment[], filter: 'all' as Filter, loading: false }),
  withComputed(({ payments, filter }) => ({
    filtered: computed(() => filter() === 'all'
      ? payments()
      : payments().filter(p => p.status === filter())),
  })),
  withMethods((store, api = inject(PaymentApi)) => ({
    load: rxMethod<void>(pipe(
      tap(() => patchState(store, { loading: true })),
      switchMap(() => api.list().pipe(
        tap((payments) => patchState(store, { payments, loading: false })),
      )),
    )),
  })),
);
```

## Normalization for Large Collections

```typescript
// BAD: array of nested objects → deep updates copy whole tree
state.posts = state.posts.map(p =>
  p.id === id ? { ...p, comments: [...p.comments, comment] } : p);

// GOOD: normalized by id, O(1) updates
type State = {
  posts:    { byId: Record<string, Post>;    allIds: string[] };
  comments: { byId: Record<string, Comment>; allIds: string[] };
};
state.comments.byId[comment.id] = comment;
state.posts.byId[postId].commentIds.push(comment.id);
```

Use Immer (`produce`) or RTK's createEntityAdapter to keep this ergonomic.

## Decision Matrix

| Need | Choose |
|---|---|
| Server data with caching/refetch | TanStack Query / SWR / RTK Query |
| Small client UI state (theme, modal) | useState / signals / Pinia |
| Cross-route client state (cart, filters) | Zustand / Jotai / Pinia |
| Complex derived state, time-travel debug | Redux Toolkit / NgRx |
| Form state | react-hook-form / VeeValidate / Angular reactive forms |

