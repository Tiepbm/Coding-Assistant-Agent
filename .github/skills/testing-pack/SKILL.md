---
name: testing-pack
description: 'Use when writing or designing tests: unit tests, integration tests, E2E tests, TDD workflow, mocking strategy, or test coverage analysis across any stack.'
---
# Testing Pack

## When to Use
- Writing unit tests for services, components, utilities.
- Writing integration tests with real databases or message brokers.
- Writing E2E tests with Playwright, Cypress, or mobile test frameworks.
- Applying TDD red-green-refactor workflow.
- Choosing mocking strategy (what to mock, what to use real).
- Analyzing or improving test coverage.

## When NOT to Use
- Implementing the production code itself → `backend-pack` or `frontend-pack`.
- Debugging a failing test's root cause → `debugging-pack`.
- CI/CD pipeline that runs tests → `devops-pack`.
- Code review of test quality → `quality-pack`.

## Pack Reference Map
| Reference | Use when |
|---|---|
| `unit-testing` | Writing unit tests per framework (JUnit, xUnit, Jest/Vitest, pytest), AAA pattern, mocking. |
| `integration-testing` | Testing with real databases (Testcontainers), HTTP mocking (MSW, WireMock), broker tests. |
| `e2e-testing` | Browser tests (Playwright, Cypress), mobile tests (Detox, Maestro), Page Object pattern. |
| `tdd-workflow` | Red-Green-Refactor cycle, test-first discipline, when to TDD vs when to skip. |

## Cross-Pack Handoffs
- → `backend-pack` for the production code being tested.
- → `frontend-pack` for component test patterns (Testing Library).
- → `debugging-pack` when a test failure needs root cause analysis.
- → `devops-pack` for CI pipeline test configuration.
- → `quality-pack` for test code review and coverage thresholds.
