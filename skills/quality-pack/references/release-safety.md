---
name: release-safety
description: 'Use when shipping a risky change: feature flag rollout %, kill switch, rollback drill, expand-contract migration coordination, SLO gate in CI. Implementation patterns; defers SLO definition + rollout policy to CE7.'
---
# Release Safety (Implementation Patterns)

> Defers to CE7 for: SLO target numbers, rollout policy (1%/10%/50%/100% vs blue-green vs shadow), error-budget burn alerts, postmortem ownership. See `software-engineering-agent/skills/observability-release-pack/references/devops-and-release.md` and `monitoring-alerting-and-slos.md`.

## When to Use
- Wrapping a new code path in a feature flag with a kill switch.
- Implementing percentage-based rollout deterministically (consistent hashing on `tenant_id`/`user_id`).
- Wiring a SLO gate into CI / deploy pipeline (abort if p99 / error_rate breach over a window).
- Drafting a rollback drill (how to verify rollback works *before* prod).
- Coordinating expand→migrate→contract steps with a feature flag.

## When NOT to Use
- Defining the SLO target number → CE7 `observability-release-pack/monitoring-alerting-and-slos`.
- Choosing rollout strategy (canary vs blue-green vs shadow) → CE7 `observability-release-pack/devops-and-release`.
- Incident-response process / postmortem ownership → CE7 `observability-release-pack/incident-response-and-postmortem`.

## BAD vs GOOD: Feature flag with kill switch

BAD — flag check buried, no kill switch:
```ts
if (process.env.NEW_PAYMENT_FLOW === 'true') { useNewFlow(); }
```

GOOD — provider-driven flag, deterministic rollout, kill switch, audit log:
```ts
import { OpenFeature } from '@openfeature/server-sdk';
const client = OpenFeature.getClient();

const flagKey = 'payments.idempotent_v2';
const ctx = { targetingKey: tenantId, attributes: { userId } };
const enabled = await client.getBooleanValue(flagKey, false, ctx);

if (enabled) {
  log.info({ flag: flagKey, decision: true, tenantId, correlationId }, 'flag.evaluated');
  await useNewFlow(req);
} else {
  await useLegacyFlow(req);
}
```

`flag.evaluated` log + the metric `feature_flag_evaluation_total{flag,decision}` lets ops verify rollout reached the intended cohort.

## SLO gate in CI (deploy abort)

Pseudocode for a post-deploy verification step (run for 30 min after each rollout step):

```bash
# After deploy step (e.g., 10% rollout)
sleep 1800   # observe for 30 min
P99=$(curl -s "$PROM/api/v1/query?query=histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=\"payments\",route=\"/v1/payments/capture\"}[5m])) by (le))" | jq '.data.result[0].value[1]|tonumber')
ERR_RATE=$(curl -s "$PROM/api/v1/query?query=sum(rate(http_requests_total{service=\"payments\",code=~\"5..\"}[5m])) / sum(rate(http_requests_total{service=\"payments\"}[5m]))" | jq '.data.result[0].value[1]|tonumber')
if (( $(echo "$P99 > 0.35" | bc -l) )) || (( $(echo "$ERR_RATE > 0.005" | bc -l) )); then
  echo "SLO gate breach: p99=${P99}s, err=${ERR_RATE}. Rolling back."
  ./scripts/flag-disable.sh payments.idempotent_v2
  exit 1
fi
```

## Rollback drill (do this BEFORE prod)

1. Deploy to staging with flag at 100%.
2. Flip the flag to 0% via the provider's admin API (not a redeploy).
3. Verify: traffic on legacy path, no 5xx spike, no orphan rows in new schema column.
4. Document the exact command / dashboard query used in the runbook (see `runbook-snippets`).
5. Time it. Rollback that takes > 5 min in staging will take > 30 min in prod.

## Expand → Migrate → Contract with a flag

Three deploys, never collapse them:

1. **Expand** — add the new column / table / index without code reads from it. Backfill in batches.
2. **Migrate** — flip the flag to read/write new path; legacy path remains as fallback for one full release cycle.
3. **Contract** — remove the old column / code path AFTER the flag is at 100% for ≥ N days with no rollback.

If the migration cannot be executed in three deploys, **escalate to CE7** for a custom plan.

## Cross-Pack Handoffs
- Flag SDK + provider patterns → `quality-pack/feature-flags`.
- Metric / log emission for the flag → `observability-pack/metrics-instrumentation` + `observability-pack/structured-logging`.
- CI/CD pipeline wiring → `devops-pack/ci-cd-pipelines`.
- Runbook entry for the rollout → `observability-pack/runbook-snippets`.
- SLO target number / rollout policy / postmortem ownership → CE7 `observability-release-pack/*`.

