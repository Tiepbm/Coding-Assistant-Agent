---
name: frontend-pack
description: 'Use when writing client-side code: UI components, hooks/signals, state management, forms, routing, SSR/SSG, or accessibility in React/Next.js, Angular, or Vue/Nuxt.'
---
# Frontend Pack

## When to Use
- UI component implementation (server components, client components, templates).
- State management (local, URL, server state, global store).
- Form handling with validation (client + server validation).
- Client-side routing, navigation guards, layouts.
- SSR/SSG/ISR rendering strategies.
- Accessibility (ARIA, keyboard navigation, focus management).

## When NOT to Use
- REST/GraphQL API implementation → `backend-pack`.
- SQL queries, ORM mappings, migrations → `database-pack`.
- E2E test strategy or Playwright/Cypress scripts → `testing-pack`.
- Docker, CI/CD, deployment → `devops-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `react-nextjs` | React 18/19 components, Next.js App Router, server components, TanStack Query, react-hook-form. |
| `angular` | Angular 17/18+ standalone components, signals, RxJS, reactive forms, functional interceptors. |
| `vue-nuxt` | Vue 3 Composition API, Nuxt 3, Pinia, composables, VeeValidate, useFetch/useAsyncData. |
| `accessibility` | a11y patterns: semantic HTML, ARIA, focus management, keyboard nav, jest-axe testing. |
| `state-management-advanced` | Zustand/Jotai/Redux Toolkit/Pinia/NgRx Signals, server-vs-client state separation, normalization, optimistic updates. |

## Cross-Pack Handoffs
- → `backend-pack` for API contracts, CORS config, auth token flow.
- → `testing-pack` for component tests, integration tests, E2E tests.
- → `quality-pack` for accessibility audit, code review of UI code.
- → `database-pack` when frontend queries DB directly (e.g., Prisma in Next.js server actions).
- → `mobile-pack` when building React Native instead of web React.
