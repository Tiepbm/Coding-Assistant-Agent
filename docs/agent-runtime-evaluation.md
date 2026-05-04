# Agent Runtime Evaluation — Production-Grade Grader Catalog

> Production evaluation contract for the **CE7 + Coding Assistant** Agent Workflow pair. Inspired by AWS Bedrock AgentCore Evaluations, OpenAI Agents SDK *Evaluate agent workflows*, Anthropic *Demystifying Evals*, and Anthropic *Effective harnesses for long-running agents*.
>
> Mirrored byte-for-byte at:
> - `software-engineering-agent/docs/agent-runtime-evaluation.md` (canonical)
> - `coding-assistant-agent/docs/agent-runtime-evaluation.md`

## 1. Why this exists

`evals/rubric.md` grades the **content** of one response. This document grades the **trajectory** an agent took to produce it: which packs were activated, how many turns, how many tool calls, how many tokens, whether guardrails fired correctly, whether the handoff package was complete.

In production, a wrong path to a right answer is still a defect (cost, latency, fragility). This catalog defines the graders that catch those defects.

## 2. Grader catalog

Every grader returns `pass | fail | n/a` plus a numeric score. Aggregate scores feed `evals/run_eval.py` v2.

### 2.1 Routing accuracy grader

| Field | Value |
|---|---|
| Inspired by | AWS AgentCore "tool-call accuracy", OpenAI Agents SDK tracing |
| Inputs | `expected_pack`, `expected_references`, `packs_invoked[]`, `references_invoked[]` |
| Pass | All expected packs and references appear in invoked sets; no extra pack outside `expected_pack ∪ expected_addons` |
| Score | `1.0 − (missed + spurious) / max(expected, 1)` |
| Owner | both agents |

### 2.2 Trajectory efficiency grader

| Field | Value |
|---|---|
| Inspired by | Anthropic harness paper (turn budget), AWS AgentCore (latency) |
| Inputs | `n_turns`, `n_toolcalls`, `tokens_total`, `latency_ms`, per-task `budget` |
| Pass | All four ≤ budget × 1.0; warn if any > budget × 0.8 |
| Score | weighted: 0.4 turns, 0.3 toolcalls, 0.2 tokens, 0.1 latency |
| Owner | both agents |

### 2.3 Goal accuracy grader (LLM-as-judge)

| Field | Value |
|---|---|
| Inspired by | AWS AgentCore Evaluations |
| Inputs | task `goal`, agent final answer, optional reference solution |
| Method | Judge model rates `goal_met` ∈ {0, 0.5, 1} with rationale; chain-of-thought hidden, only verdict + 1-line reason emitted |
| Pass | `goal_met ≥ 0.5` for capability tier, `= 1.0` for regression tier |
| Owner | both agents |

### 2.4 Response completeness grader

| Field | Value |
|---|---|
| Inspired by | AWS AgentCore "response completeness" |
| Inputs | `must_include[]`, `must_not_include[]`, agent response text |
| Pass | 100% of `must_include` hit; zero `must_not_include` hit |
| Score | `0.7 × inclusion_ratio − 0.3 × forbidden_ratio` clamped to `[0, 1]` |
| Owner | Coding |

### 2.5 Guardrail-fired grader

| Field | Value |
|---|---|
| Inspired by | OpenAI Agents SDK guardrails |
| Inputs | task `expected_guardrails[]` (e.g., `["output:hardcoded-secret"]`), `guardrails_triggered[]` |
| Pass | Expected guardrails are present in triggered set; no spurious triggers |
| Owner | both agents (Coding output guardrails, CE7 input guardrails) |

### 2.6 Handoff completeness grader (CE7 → Coding)

| Field | Value |
|---|---|
| Inspired by | OpenAI Agents SDK *handoffs*, this repo's HANDOFF-PROTOCOL |
| Inputs | CE7 response YAML, expected fields per `HANDOFF-PROTOCOL.md §3` |
| Pass | All required fields present (`adr_id`, `contract`, `idempotency` if state-changing, `slo` if new endpoint, `rollout`, `runbook_stub`, `on_call_owner`); each ≥ 1 line, no `TODO`/`tbd` |
| Score | fields_present / fields_required |
| Owner | CE7 |

### 2.7 Self-Review block grader (Coding → CE7)

| Field | Value |
|---|---|
| Inspired by | this repo's HANDOFF-PROTOCOL §4 |
| Inputs | Coding response YAML, expected fields per §4 |
| Pass | `production_readiness_mini_bar` all rows declared (PASS/FAIL/N/A); `self_review_checklist` ≥ 80% PASS; `residual_risks` declared (or explicit "none") |
| Owner | Coding |

### 2.8 Re-engagement-correctness grader

| Field | Value |
|---|---|
| Inspired by | HANDOFF-PROTOCOL §5 |
| Inputs | task scenario + `expected_action` (`implement` | `escalate-to-ce7`) |
| Pass | Coding escalates iff scenario matches §5 trigger; does not escalate when implementation is appropriate |
| Owner | Coding (`evals/handoff-benchmark.jsonl`) |

### 2.9 Anti-pattern grader

| Field | Value |
|---|---|
| Inspired by | OpenAI graders (red-line tests) |
| Inputs | `must_not_do[]`, `must_do[]`, agent code |
| Pass | Zero `must_not_do` patterns; all `must_do` patterns present |
| Severity | regression-tier only; **any** failure is a CI block on protected branches |
| Owner | both agents (`anti-pattern-benchmark.jsonl`) |

### 2.10 Token budget grader

| Field | Value |
|---|---|
| Inspired by | Anthropic context engineering, AWS cost guardrail |
| Inputs | per-task `token_budget`, `tokens_total` |
| Pass | `tokens_total ≤ token_budget` |
| Score | `min(1.0, token_budget / tokens_total)` |
| Owner | both agents |

### 2.11 Trajectory grader (sequence of pack invocations)

| Field | Value |
|---|---|
| Inspired by | AWS "trajectory evaluation" lessons-learned post |
| Inputs | `expected_trajectory[]` (ordered list of pack/reference activations), actual sequence |
| Method | Edit-distance (Levenshtein) between expected and actual sequences |
| Pass | edit-distance ≤ 1 for regression tier, ≤ 3 for capability |
| Owner | both agents |

## 3. Tier × grader matrix

|  | regression | capability | holdout |
|---|---|---|---|
| Routing accuracy | required | required | required |
| Trajectory efficiency | required (strict budget) | required (loose budget) | required (loose budget) |
| Goal accuracy (LLM-judge) | required = 1.0 | required ≥ 0.5 | required ≥ 0.5 |
| Response completeness | required = 1.0 | required ≥ 0.7 | required ≥ 0.7 |
| Guardrail-fired | required iff `expected_guardrails` set | required iff set | required iff set |
| Handoff completeness | n/a (Coding repo) ; required (CE7) | required | required |
| Self-Review block | required (Coding) | required | required |
| Re-engagement correctness | required iff handoff scenario | required | required |
| Anti-pattern | **CI-blocking** = 100% pass | **CI-blocking** = 100% pass | **CI-blocking** |
| Token budget | required | warn | warn |
| Trajectory grader | edit-distance ≤ 1 | edit-distance ≤ 3 | edit-distance ≤ 3 |

## 4. Production monitoring (live traffic)

When agents run on real tickets, the same graders apply with relaxed thresholds. Track these as **service-level indicators** for the agent itself:

| SLI | Definition | Target |
|---|---|---|
| Routing-accuracy SLO | rolling 7-day pass rate of grader 2.1 on real tickets | ≥ 92% |
| Token-cost SLO | p95 `tokens_total` per ticket | ≤ 1.2 × benchmark median |
| Re-engagement-correctness | % handoffs rated correct by CE7 reviewer in spot-check | ≥ 90% |
| Guardrail false-positive | % blocked outputs reviewer overturns | ≤ 5% |
| Mini-Bar pass rate (Coding) | % money/state/PII tickets where all 5 rows = PASS | ≥ 95% |
| Production-Bar honor (CE7) | % production-critical tickets with no `Stop if missing` violation | 100% |

Alert thresholds and runbook owners live in `observability-release-pack/monitoring-alerting-and-slos`.

## 5. Eval lifecycle

1. **Author task** with: `goal`, `expected_pack`, `expected_references`, `must_include`, `must_not_include`, `tier`, optional `token_budget`, optional `expected_guardrails`, optional `expected_trajectory`.
2. **Run dev tier** (`regression + capability`) locally before commit.
3. **CI runs all tiers including holdout**; fails if any anti-pattern fails or if pass rate < tier threshold.
4. **Promote/demote** tasks per rules in `evals/eval-tiers.md`.
5. **Quarterly review**: prune saturated capability tasks (>95% pass for 3 months → promote to regression); add new frontier tasks.

## 6. References

- Anthropic — *Demystifying Evals for AI Agents*
- Anthropic — *Effective harnesses for long-running agents*
- Anthropic — *Effective context engineering for AI agents*
- AWS — *Build reliable AI agents with Amazon Bedrock AgentCore Evaluations*
- AWS — *Evaluating AI agents: Real-world lessons from building agentic systems at Amazon*
- OpenAI — *Evaluate agent workflows*
- OpenAI — *Agents SDK* (handoffs, guardrails, tracing)
- Google — *Agent Development Kit*

