---
name: feature-flags
description: 'Feature-flag implementation patterns: SDK integration (LaunchDarkly, Unleash, OpenFeature), kill-switches, percentage rollouts, scoped flags, testing.'
---
# Feature Flags Code Patterns

## Flag Types — Choose Intentionally

| Type | Lifetime | Example |
|---|---|---|
| **Release** | days–weeks | New checkout flow rollout |
| **Experiment** | weeks | A/B test pricing copy |
| **Ops / Kill-switch** | permanent | Disable expensive recommender during incident |
| **Permission** | permanent | Beta feature for specific tenant |

Anti-pattern: experiment flag still alive after 6 months → becomes implicit config. Set expiry on creation.

## OpenFeature (vendor-neutral) — Backend

```typescript
// Provider setup once at startup
import { OpenFeature } from '@openfeature/server-sdk';
import { UnleashProvider } from '@openfeature/unleash-provider';

await OpenFeature.setProviderAndWait(new UnleashProvider({
  url: process.env.UNLEASH_URL!,
  appName: 'payments-api',
  instanceId: process.env.HOSTNAME!,
}));

const client = OpenFeature.getClient();

// Evaluate per request with full context
async function chargePayment(req: Request) {
  const ctx = {
    targetingKey: req.user.id,
    tenantId: req.user.tenantId,
    country: req.geo.country,
  };
  const useNewProcessor = await client.getBooleanValue('payments.new-processor', false, ctx);
  return useNewProcessor
    ? newProcessor.charge(req.body)
    : legacyProcessor.charge(req.body);
}
```

## Java / Spring (OpenFeature)

```java
@Service
@RequiredArgsConstructor
public class PaymentService {
    private final Client featureClient;  // OpenFeature client bean

    public Payment charge(ChargeRequest request) {
        var ctx = new MutableContext(request.userId())
            .add("tenantId", request.tenantId().toString())
            .add("amount", request.amount().doubleValue());

        if (featureClient.getBooleanValue("payments.new-processor", false, ctx)) {
            return newProcessor.charge(request);
        }
        return legacyProcessor.charge(request);
    }
}
```

## Frontend (React + LaunchDarkly)

```tsx
// Provider at root
<LDProvider clientSideID={LD_KEY} context={{ kind: 'user', key: user.id, tenantId }}>
  <App />
</LDProvider>

// Component
const flags = useFlags();
return flags['checkout.new-flow']
  ? <NewCheckout />
  : <LegacyCheckout />;
```

## Anti-Pattern: Flag Spaghetti

```typescript
// BAD: nested flags, branching everywhere
if (flags.newCheckout) {
  if (flags.newPaymentMethod) {
    if (flags.experimentalUI) { /* 3 branches deep */ }
  }
}

// GOOD: extract variants behind a strategy interface
interface CheckoutStrategy { render(): JSX.Element; }
const strategy: CheckoutStrategy = pickStrategy(flags); // single decision point
return strategy.render();
```

## Kill-Switch Pattern (Ops)

```typescript
// Wrap expensive/risky calls; default = enabled, flip = disabled
async function recommend(userId: string) {
  if (await client.getBooleanValue('ops.recommender-enabled', true, { targetingKey: userId })) {
    return recommender.compute(userId);
  }
  return fallbackTopSellers(); // graceful degradation
}
```

Always default kill-switches to **safe** value if SDK unavailable (`getBooleanValue(flag, SAFE_DEFAULT, ctx)`).

## Percentage Rollout (Server-side, Deterministic)

```typescript
// If no provider available, deterministic hash for stable bucketing
import { createHash } from 'node:crypto';

function inRollout(userId: string, flagName: string, percentage: number): boolean {
  const hash = createHash('sha256').update(`${flagName}:${userId}`).digest();
  const bucket = hash.readUInt32BE(0) % 10_000;
  return bucket < percentage * 100;
}
// inRollout(userId, 'payments.new-processor', 5) → 5% rollout, stable per user
```

## Testing with Flags

```typescript
// BAD: tests depend on real flag service → flaky, env-coupled
test('checkout flow', async () => { /* flips on prod, breaks here */ });

// GOOD: inject fake provider per test
import { InMemoryProvider } from '@openfeature/in-memory-provider';

beforeEach(async () => {
  await OpenFeature.setProviderAndWait(new InMemoryProvider({
    'payments.new-processor': { variants: { on: true, off: false }, defaultVariant: 'off', disabled: false },
  }));
});

test('uses new processor when flag on', async () => {
  await OpenFeature.getClient().setContext({ targetingKey: 'u1' });
  // flip the variant for this test
  // ...assert
});
```

## Cleanup Discipline

- Tag flag with **owner** + **expiry** at creation.
- CI lints for flag-name string literals not present in flag service (dead flags).
- Track "stale flag" metric in observability dashboard (`flag_age_days > 90`).

## Cross-Pack Handoffs

- → `observability-pack/metrics-instrumentation` to emit metric per flag evaluation (variant, user bucket).
- → `testing-pack/integration-testing` for testing both branches in CI.
- → `devops-pack/ci-cd-pipelines` to gate canary deploys behind flag.

