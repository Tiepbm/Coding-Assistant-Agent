---
name: angular
description: 'Angular 17/18+ patterns: standalone components, signals, RxJS, functional interceptors, typed reactive forms, OnPush, @defer, and tests.'
---
# Angular Code Patterns

## Standalone Component

```typescript
// BAD: NgModule-based component with large module imports
@NgModule({
  declarations: [PaymentListComponent],
  imports: [CommonModule, HttpClientModule, FormsModule],
})
export class PaymentModule {}

// GOOD: Standalone component — no NgModule needed
import { Component, inject, signal, computed } from '@angular/core';
import { AsyncPipe, CurrencyPipe, DatePipe } from '@angular/common';
import { PaymentService } from './payment.service';
import { Payment } from './payment.model';

@Component({
  selector: 'app-payment-list',
  standalone: true,
  imports: [CurrencyPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loading()) {
      <app-skeleton />
    } @else {
      <ul>
        @for (payment of payments(); track payment.id) {
          <li>{{ payment.amount | currency:payment.currency }} — {{ payment.status }}</li>
        }
        @empty {
          <li>No payments found.</li>
        }
      </ul>
    }
  `,
})
export class PaymentListComponent {
  private paymentService = inject(PaymentService);

  payments = signal<Payment[]>([]);
  loading = signal(true);

  constructor() {
    this.paymentService.getAll().subscribe({
      next: (data) => {
        this.payments.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
```

## Signals Pattern

```typescript
// BAD: Complex BehaviorSubject chains for simple derived state
private amount$ = new BehaviorSubject<number>(0);
private tax$ = new BehaviorSubject<number>(0);
total$ = combineLatest([this.amount$, this.tax$]).pipe(
  map(([amount, tax]) => amount + tax)
);

// GOOD: Signals for synchronous derived state
import { signal, computed, effect } from '@angular/core';

export class PaymentFormComponent {
  amount = signal(0);
  taxRate = signal(0.1);
  total = computed(() => this.amount() * (1 + this.taxRate()));

  // Effect for side effects (logging, analytics)
  private logEffect = effect(() => {
    console.log(`Total updated: ${this.total()}`);
  });
}
```

## RxJS: When to Use (vs Signals)

```typescript
// Use signals for: synchronous state, UI state, derived values
// Use RxJS for: HTTP calls, WebSocket streams, complex async orchestration

// BAD: Nested subscriptions
this.route.params.subscribe(params => {
  this.paymentService.getById(params['id']).subscribe(payment => {
    this.auditService.log(payment.id).subscribe(() => {
      this.payment = payment; // Callback hell in RxJS
    });
  });
});

// GOOD: Flat RxJS pipeline with switchMap
import { switchMap, tap, catchError } from 'rxjs/operators';
import { EMPTY } from 'rxjs';

payment$ = this.route.params.pipe(
  switchMap(({ id }) => this.paymentService.getById(id)),
  tap((payment) => this.auditService.log(payment.id)),
  catchError((err) => {
    this.error.set(err.message);
    return EMPTY;
  })
);
```

## Functional Interceptors

```typescript
// BAD: Class-based interceptor (legacy pattern)
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler) { /* ... */ }
}

// GOOD: Functional interceptor (Angular 17+)
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        authService.logout();
      }
      return throwError(() => error);
    })
  );
};

export const correlationIdInterceptor: HttpInterceptorFn = (req, next) => {
  const correlationId = crypto.randomUUID();
  return next(req.clone({
    setHeaders: { 'X-Correlation-Id': correlationId },
  }));
};

// Registration in app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([correlationIdInterceptor, authInterceptor])),
  ],
};
```

## Typed Reactive Forms

```typescript
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'app-payment-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <label for="amount">Amount</label>
      <input id="amount" type="number" formControlName="amount"
             [attr.aria-invalid]="form.controls.amount.invalid && form.controls.amount.touched" />
      @if (form.controls.amount.errors?.['min']) {
        <p role="alert">Amount must be positive</p>
      }

      <label for="currency">Currency</label>
      <input id="currency" formControlName="currency" maxlength="3"
             [attr.aria-invalid]="form.controls.currency.invalid && form.controls.currency.touched" />

      <button type="submit" [disabled]="form.invalid || submitting()">
        {{ submitting() ? 'Submitting…' : 'Create Payment' }}
      </button>
    </form>
  `,
})
export class PaymentFormComponent {
  private fb = inject(FormBuilder);
  private paymentService = inject(PaymentService);

  submitting = signal(false);

  form = this.fb.nonNullable.group({
    amount: [0, [Validators.required, Validators.min(0.01)]],
    currency: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(3)]],
    sourceAccount: ['', Validators.required],
    destAccount: ['', Validators.required],
  });

  onSubmit() {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.paymentService.create(this.form.getRawValue()).subscribe({
      next: () => this.form.reset(),
      error: () => this.submitting.set(false),
      complete: () => this.submitting.set(false),
    });
  }
}
```

## State Management Ladder

```typescript
// 1. Signals — local/component state (default choice)
count = signal(0);

// 2. Component Store — feature-level state
import { signalStore, withState, withMethods, patchState } from '@ngrx/signals';

export const PaymentStore = signalStore(
  withState({ payments: [] as Payment[], loading: false }),
  withMethods((store, paymentService = inject(PaymentService)) => ({
    load() {
      patchState(store, { loading: true });
      paymentService.getAll().subscribe({
        next: (payments) => patchState(store, { payments, loading: false }),
        error: () => patchState(store, { loading: false }),
      });
    },
  }))
);

// 3. NgRx Store — app-wide state with complex side effects (use sparingly)
// Only when: multiple features share state, undo/redo, time-travel debugging needed
```

## @defer + SSR/Hydration

```typescript
@Component({
  template: `
    <!-- Lazy-load heavy component -->
    @defer (on viewport) {
      <app-payment-chart [data]="payments()" />
    } @placeholder {
      <div class="h-64 bg-gray-100 animate-pulse"></div>
    } @loading (minimum 300ms) {
      <app-spinner />
    }
  `,
})
export class DashboardComponent {}
```

## Test: Jest + Testing Library + HttpTestingController

```typescript
import { render, screen, fireEvent } from '@testing-library/angular';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PaymentFormComponent } from './payment-form.component';

describe('PaymentFormComponent', () => {
  it('submits valid form', async () => {
    const { fixture } = await render(PaymentFormComponent, {
      providers: [provideHttpClient(), provideHttpClientTesting(), PaymentService],
    });

    const httpMock = fixture.debugElement.injector.get(HttpTestingController);

    const amountInput = screen.getByLabelText('Amount');
    const currencyInput = screen.getByLabelText('Currency');

    fireEvent.input(amountInput, { target: { value: '100' } });
    fireEvent.input(currencyInput, { target: { value: 'VND' } });
    fireEvent.click(screen.getByRole('button', { name: /create payment/i }));

    const req = httpMock.expectOne('/api/payments');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.amount).toBe(100);
    req.flush({ id: 'pay-1', status: 'PENDING' });

    httpMock.verify();
  });

  it('shows validation error for negative amount', async () => {
    await render(PaymentFormComponent, {
      providers: [provideHttpClient(), provideHttpClientTesting(), PaymentService],
    });

    const amountInput = screen.getByLabelText('Amount');
    fireEvent.input(amountInput, { target: { value: '-5' } });
    fireEvent.blur(amountInput);

    expect(screen.getByRole('alert')).toHaveTextContent('Amount must be positive');
  });
});
```

## Anti-Patterns

- **Nested subscriptions**: Use `switchMap`/`concatMap`/`mergeMap` instead.
- **switchMap for write operations**: Use `concatMap` for POST/PUT/DELETE (switchMap cancels in-flight).
- `subscribe()` without `takeUntilDestroyed()` — memory leaks.
- `ChangeDetectionStrategy.Default` everywhere — poor performance with large lists.
- `any` in HTTP responses — use typed generics `http.get<Payment[]>(...)`.
- Manual `ngOnInit` data loading without error/loading state.
- Importing entire RxJS: `import * as rxjs from 'rxjs'`.

## Gotchas

- `inject()` only works in constructor or field initializer — not in methods.
- `takeUntilDestroyed()` must be called in injection context (constructor).
- Signals are synchronous — don't use for async operations (use RxJS + `toSignal()`).
- `@defer` requires Angular 17+ and does NOT work with SSR pre-rendering.
- `provideHttpClient(withFetch())` uses `fetch` API — different error behavior than XHR.
- Reactive forms `getRawValue()` includes disabled controls; `value` does not.
- Zone.js removal (experimental in 18) requires explicit change detection triggers.
