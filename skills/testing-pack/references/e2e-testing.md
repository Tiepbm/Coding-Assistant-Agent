---
name: e2e-testing
description: 'E2E testing patterns: Playwright (cross-browser, API), Cypress (component + E2E), Detox/Maestro (mobile), Page Object pattern.'
---
# E2E Testing Patterns

## Playwright — Cross-Browser E2E

```typescript
// BAD: Fragile selectors, no waiting, no assertions
test('create payment', async ({ page }) => {
  await page.goto('/payments');
  await page.click('.btn-primary'); // Fragile CSS selector
  await page.fill('#amount', '100');
  await page.click('button'); // Which button?
  // No assertion
});

// GOOD: Accessible selectors, explicit waits, clear assertions
import { test, expect } from '@playwright/test';

test('creates payment and shows in list', async ({ page }) => {
  await page.goto('/payments');

  // Use accessible selectors
  await page.getByRole('link', { name: 'New Payment' }).click();
  await page.getByLabel('Amount').fill('100');
  await page.getByLabel('Currency').fill('VND');
  await page.getByLabel('Source Account').fill('ACC-001');
  await page.getByLabel('Destination Account').fill('ACC-002');
  await page.getByRole('button', { name: 'Create Payment' }).click();

  // Assert navigation and content
  await expect(page).toHaveURL('/payments');
  await expect(page.getByText('VND 100')).toBeVisible();
  await expect(page.getByText('PENDING')).toBeVisible();
});

test('shows validation errors for empty form', async ({ page }) => {
  await page.goto('/payments/new');

  await page.getByRole('button', { name: 'Create Payment' }).click();

  await expect(page.getByText('Amount must be positive')).toBeVisible();
  await expect(page.getByText('Required')).toHaveCount(2); // source + dest
});
```

## Playwright — API Testing

```typescript
import { test, expect } from '@playwright/test';

test.describe('Payment API', () => {
  test('POST /api/payments returns 201', async ({ request }) => {
    const response = await request.post('/api/payments', {
      data: {
        tenantId: crypto.randomUUID(),
        idempotencyKey: crypto.randomUUID(),
        amount: 100,
        currency: 'VND',
        sourceAccount: 'ACC-001',
        destAccount: 'ACC-002',
      },
    });

    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body.status).toBe('PENDING');
    expect(body.id).toBeTruthy();
  });

  test('GET /api/payments returns list', async ({ request }) => {
    const response = await request.get('/api/payments');

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });
});
```

## Page Object Pattern

```typescript
// pages/PaymentListPage.ts
import { Page, Locator, expect } from '@playwright/test';

export class PaymentListPage {
  readonly page: Page;
  readonly newPaymentLink: Locator;
  readonly paymentRows: Locator;
  readonly searchInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.newPaymentLink = page.getByRole('link', { name: 'New Payment' });
    this.paymentRows = page.getByRole('row').filter({ hasNot: page.getByRole('columnheader') });
    this.searchInput = page.getByPlaceholder('Search payments');
  }

  async goto() {
    await this.page.goto('/payments');
  }

  async createPayment(data: { amount: string; currency: string }) {
    await this.newPaymentLink.click();
    await this.page.getByLabel('Amount').fill(data.amount);
    await this.page.getByLabel('Currency').fill(data.currency);
    await this.page.getByRole('button', { name: 'Create Payment' }).click();
    await expect(this.page).toHaveURL('/payments');
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
  }

  async expectPaymentCount(count: number) {
    await expect(this.paymentRows).toHaveCount(count);
  }
}

// Usage in test
test('search filters payments', async ({ page }) => {
  const paymentList = new PaymentListPage(page);
  await paymentList.goto();
  await paymentList.search('ACC-001');
  await paymentList.expectPaymentCount(1);
});
```

## Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['junit', { outputFile: 'test-results/e2e.xml' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'mobile', use: { ...devices['iPhone 14'] } },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

## Cypress — Component + E2E

```typescript
// E2E test
describe('Payment Flow', () => {
  beforeEach(() => {
    cy.intercept('GET', '/api/payments', { fixture: 'payments.json' }).as('getPayments');
    cy.visit('/payments');
    cy.wait('@getPayments');
  });

  it('creates a new payment', () => {
    cy.intercept('POST', '/api/payments', {
      statusCode: 201,
      body: { id: 'pay-1', status: 'PENDING', amount: 100 },
    }).as('createPayment');

    cy.findByRole('link', { name: /new payment/i }).click();
    cy.findByLabelText('Amount').type('100');
    cy.findByLabelText('Currency').type('VND');
    cy.findByRole('button', { name: /create payment/i }).click();

    cy.wait('@createPayment');
    cy.url().should('include', '/payments');
    cy.findByText('PENDING').should('be.visible');
  });
});

// Component test
import { mount } from 'cypress/react';
import { PaymentForm } from './PaymentForm';

describe('PaymentForm', () => {
  it('validates required fields', () => {
    const onSubmit = cy.stub().as('onSubmit');
    mount(<PaymentForm onSubmit={onSubmit} />);

    cy.findByRole('button', { name: /create/i }).click();
    cy.findByText(/amount must be positive/i).should('be.visible');
    cy.get('@onSubmit').should('not.have.been.called');
  });
});
```

## Mobile: Detox (React Native)

```typescript
import { device, element, by, expect } from 'detox';

describe('Payment Flow', () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
  });

  it('creates payment from mobile', async () => {
    await element(by.id('tab-payments')).tap();
    await element(by.id('btn-new-payment')).tap();

    await element(by.id('input-amount')).typeText('100');
    await element(by.id('input-currency')).typeText('VND');
    await element(by.id('btn-submit')).tap();

    await expect(element(by.text('Payment Created'))).toBeVisible();
    await expect(element(by.text('PENDING'))).toBeVisible();
  });
});
```

## Anti-Patterns

- **E2E for every edge case**: E2E tests are slow — use unit/integration for edge cases.
- **Flaky selectors**: `cy.get('.btn-primary:nth-child(3)')` — use `getByRole`, `getByLabel`, `data-testid`.
- `cy.wait(5000)` — use `cy.wait('@alias')` or Playwright auto-waiting.
- Testing third-party UI (date pickers, modals) in E2E — mock or stub them.
- No test data cleanup — tests pollute each other's state.
- Running E2E in parallel against shared database — use isolated test data.

## Gotchas

- Playwright auto-waits for elements — don't add manual `waitForSelector` unless needed.
- Cypress runs in the browser — cannot use Node.js APIs directly (use `cy.task`).
- Detox requires a built app binary — add build step to CI.
- `page.getByRole('button')` matches `<button>` and `<input type="button">` and `role="button"`.
- Playwright `trace: 'on-first-retry'` — traces only on retry, saves CI storage.
- Cypress `cy.intercept` must be set up BEFORE the action that triggers the request.
