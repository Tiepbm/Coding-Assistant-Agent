---
name: accessibility
description: 'Web a11y patterns: semantic HTML, ARIA, focus management, keyboard navigation, screen-reader testing per framework.'
---
# Accessibility (a11y) Code Patterns

## Semantic HTML First (ARIA second)

```tsx
// BAD: div soup, no semantics, mouse-only
<div onClick={submit} className="btn">Submit</div>

// GOOD: native button, keyboard works, focus styles preserved
<button type="submit" onClick={submit} className="btn">
  Submit
</button>
```

Rule: if a native element exists (`<button>`, `<a>`, `<label>`, `<nav>`, `<main>`), use it. ARIA is a **patch**, not a replacement.

## Form Labeling + Error Association

```tsx
// BAD: placeholder as label, error not announced
<input placeholder="Email" />
{error && <span>{error}</span>}

// GOOD: label + aria-describedby + role="alert" for live announcement
<label htmlFor="email">Email</label>
<input
  id="email"
  type="email"
  required
  aria-invalid={!!error}
  aria-describedby={error ? 'email-error' : undefined}
/>
{error && <span id="email-error" role="alert">{error}</span>}
```

## Focus Management (route changes, modals)

```tsx
// On route change — move focus to <h1> so screen readers announce new page
useEffect(() => {
  document.querySelector<HTMLHeadingElement>('h1')?.focus();
}, [pathname]);

// Modal — trap focus, return on close
import { FocusTrap } from 'focus-trap-react';
<FocusTrap active={open} focusTrapOptions={{ returnFocusOnDeactivate: true }}>
  <div role="dialog" aria-modal="true" aria-labelledby="dlg-title">
    <h2 id="dlg-title">Confirm payment</h2>
    {/* ... */}
  </div>
</FocusTrap>
```

## Keyboard Navigation Checklist

- All interactive elements reachable via `Tab` (no `tabIndex={-1}` unless removing from order intentionally).
- Visible focus indicator (`:focus-visible` outline ≥ 2px, contrast ≥ 3:1).
- `Esc` closes modals/menus.
- `Enter`/`Space` activate buttons; `Enter` only for links.
- Skip-to-content link as first focusable element.

## Angular — CDK a11y

```typescript
import { LiveAnnouncer, FocusMonitor, FocusTrap, ConfigurableFocusTrapFactory } from '@angular/cdk/a11y';

constructor(private announcer: LiveAnnouncer) {}

submit() {
  this.api.create(...).subscribe({
    next: () => this.announcer.announce('Payment created', 'polite'),
    error: (e) => this.announcer.announce(`Error: ${e.message}`, 'assertive'),
  });
}
```

## Vue — official a11y plugin / composables

```vue
<script setup>
import { useFocusTrap } from '@vueuse/integrations/useFocusTrap';
const dialog = ref(null);
const { activate, deactivate } = useFocusTrap(dialog);
</script>

<template>
  <div ref="dialog" role="dialog" aria-modal="true" :aria-labelledby="titleId">
    <h2 :id="titleId">{{ title }}</h2>
  </div>
</template>
```

## Testing a11y

```typescript
// Vitest + jest-axe
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('PaymentForm has no a11y violations', async () => {
  const { container } = render(<PaymentForm />);
  expect(await axe(container)).toHaveNoViolations();
});

// Playwright
const a11y = await new AxeBuilder({ page }).analyze();
expect(a11y.violations).toEqual([]);
```

## Verification

```bash
# Lint: eslint-plugin-jsx-a11y, vue-a11y, @angular-eslint/template/accessibility
npx eslint --plugin jsx-a11y src/
# Lighthouse a11y score ≥ 95
npx lighthouse http://localhost:3000 --only-categories=accessibility
```

## Quick WCAG Checklist (per PR)

- Color contrast: text ≥ 4.5:1, large text ≥ 3:1, UI components ≥ 3:1.
- Images have meaningful `alt` (or `alt=""` if decorative).
- Forms labeled, errors associated, required indicated beyond color.
- All functionality available via keyboard.
- Page has a single `<h1>`; headings nested logically.
- `lang` attribute on `<html>`.
- No `autoplay` audio/video without controls.

