# Eval Tiers — Capability vs Regression

> Inspired by Anthropic *Demystifying Evals*, AWS Bedrock AgentCore Evaluations, and OpenAI Agents SDK *Evaluate agent workflows*. Each task in `evals/*.jsonl` belongs to **exactly one** tier — declared here, not in the JSONL line, so the JSONL stays cheap to diff.

## Tier definitions

| Tier | Question it answers | Expected pass rate | Used for |
|---|---|---|---|
| **regression** | "Does the agent still handle tasks it used to?" | ≥ 95% (CI gate) | Block merges that lose ground. Stable, well-scoped, single-pack tasks. |
| **capability** | "What can this agent do well at the frontier?" | 30–70% (start low, grow) | Drive improvement. Stretch tasks: multi-file, multi-pack, ambiguous, expert-judgment. |
| **holdout** | "Are we overfitting to the dev set?" | within 10 pts of dev pass rate | Run only in CI; never optimized against. |

When the gap (`dev_pass_rate − holdout_pass_rate`) exceeds 10 pts → suspected overfit; pause prompt edits and investigate.

## Tier assignment (Coding Assistant)

### `coding-benchmark.jsonl`

- **regression** (≥95% required): `code-001`..`code-024`
- **capability** (start 50%): `code-025`..`code-029` (existing) + `code-030`..`code-039` (expert-judgment cases added in v1.2)
- **holdout** (CI only): `code-027`, `code-033`, `code-037` — DO NOT inspect these during prompt tuning

### `debugging-benchmark.jsonl`

- **regression**: all single-stack-trace tasks
- **capability**: distributed tracing / multi-service correlation tasks
- **holdout**: 20% sampled

### `tdd-benchmark.jsonl`

- **regression**: all (TDD discipline must not regress)
- **capability**: none yet
- **holdout**: 10% sampled

### `handoff-benchmark.jsonl`

- **capability** (entire file): handoff judgment is a frontier behavior; expect 60–80% pass rate.
- **holdout**: `handoff-007`, `handoff-010`

### `anti-pattern-benchmark.jsonl`

- **regression** (≥98% required — these are red lines): all 10 cases.

## Tier assignment (CE7 Software Engineering)

| File | Tier | Notes |
|---|---|---|
| `routing-benchmark.jsonl` | regression (≥95%) | Routing must not regress. |
| `banking-insurance-benchmark.jsonl` | capability (50–70%) | Domain stretch. |
| `anti-pattern-benchmark.jsonl` | regression (≥98%) | Red lines. |
| `handoff-to-coding.jsonl` | capability (60–80%) | Implementation Input Package quality. |
| `token-budget.jsonl` | regression (median ≤ budget) | Cost guardrail. |

## How to run a single tier

```bash
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$RUN_ID/responses.jsonl \
  --report   runs/$RUN_ID/report.json \
  --tier regression \
  --tiers-config evals/eval-tiers.md \
  --fail-under 95
```

```bash
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$RUN_ID/responses.jsonl \
  --report   runs/$RUN_ID/holdout-report.json \
  --tier holdout \
  --tiers-config evals/eval-tiers.md \
  --fail-under 70
```

## Maintenance rules

1. A task is **promoted** regression → capability only if it has been failing > 30 days and root cause is not a regression.
2. A task is **promoted** capability → regression once it passes 5 consecutive runs.
3. Holdout tasks are **never** read by the agent author during prompt tuning; only the CI report is consulted.
4. Adding a new reference must add at least 1 capability task (eval-driven development, per `instructions/pack-conventions.instructions.md`).

