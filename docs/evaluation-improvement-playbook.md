# Evaluation Improvement Playbook

When the eval pipeline (`docs/pipeline-guide.md`) shows regressions or low scores, follow this playbook to drive an improvement cycle.

## When to run this playbook

- Coding suite drops below 90% pass-rate.
- Any critical task (security/data-loss) fails.
- Handoff suite drops below 80%.
- Anti-pattern suite drops below 95%.
- A new model release degrades scores.

## The 5-step cycle

### 1. Read the report, find hotspots

Open `runs/<sha>/aggregate.md`. Identify:

- Top 3 lowest-scoring cases.
- Pack with the highest failure rate.
- Dimension with the highest failure rate (Routing? Inclusion? Security depth?).

### 2. Reproduce locally

For each lowest-scoring case, run the prompt manually through the agent. Compare:

- What the agent produced vs `must_include` / `must_not_include`.
- Whether the agent invoked `expected_pack` and `expected_references`.
- Whether the Self-Review Checklist + Production Readiness Mini-Bar appeared.

### 3. Diagnose: pack vs prompt vs rubric

| Symptom | Diagnosis | Fix in |
|---|---|---|
| Agent invoked the wrong pack | Routing description ambiguous | `agents/coding-assistant.agent.md` Skill Routing table OR pack `When to Use` |
| Agent invoked right pack but missed reference | Pack Reference Map ambiguous | `skills/<pack>/SKILL.md` Pack Reference Map row |
| Agent's code missed `must_include` | Reference content thin or outdated | `skills/<pack>/references/<ref>.md` |
| Agent emitted `must_not_include` | Anti-pattern not surfaced in `When NOT to Use` | Update both pack `When NOT to Use` AND `anti-pattern-benchmark.jsonl` |
| Agent skipped Self-Review | Workflow rule not strict enough | `agents/coding-assistant.agent.md` Self-Review Checklist |
| Agent failed to escalate to CE7 | Escalation signal missing | `agents/coding-assistant.agent.md` Expert Escalation table + add `handoff-benchmark.jsonl` case |

### 4. Apply the smallest fix that works

- Prefer editing a pack/reference over editing the agent (lower-risk surface).
- Prefer adding a row to a benchmark over loosening the rubric.
- Prefer making the agent ask one more clarifying question over making it guess.

### 5. Re-run + record

```bash
python3 scripts/validate_packs.py            # structural
python3 evals/validate-references.py         # cross-ref
python3 evals/run_eval.py ...                # all 3 suites
```

Append a row to `memory/learned-patterns.md` describing the bug + fix + benchmark case ID. This becomes corpus for the next regression review.

## Anti-improvements (rejected)

- Loosening `fail-under` to make CI green again.
- Removing a critical task instead of fixing it.
- Adding `must_include` to match a wrong-but-passing answer.
- Letting the agent skip Self-Review for "performance" reasons.

## Quarterly review

Every quarter (or after a significant model bump):

1. Re-read `memory/learned-patterns.md` and `memory/routing-corrections.jsonl`.
2. Identify recurring fix patterns.
3. Promote them into agent rules / pack guidance.
4. Retire anti-pattern cases that have been clean for 3+ runs (replace with harder ones).
