# Eval Rubric — Coding Assistant (Expert Edition)

Each task in `evals/*.jsonl` is graded by `run_eval.py` against the agent's response. This rubric was upgraded in v1.2.0 to score **senior-judgment dimensions** (clarify-quality, trade-off articulation, security depth, observability hooks, release safety, handoff to CE7) on top of the original deterministic dimensions.

## Schema (per JSONL line)

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Unique identifier (`code-001`, `handoff-003`, `anti-007`) |
| `prompt` | yes | Verbatim user prompt sent to the agent |
| `expected_pack` | yes | Pack the agent must route to (e.g., `backend-pack`) |
| `expected_references` | yes | Reference file(s) the agent must consult |
| `language` | yes | Primary code language of the answer |
| `must_include` | optional | Substrings/symbols that MUST appear in code blocks |
| `must_not_include` | optional | Substrings that MUST NOT appear (anti-patterns) |
| `expected_test_framework` | optional | Test framework expected in answer |
| `expected_steps` | optional | Min number of distinct deploy/code steps for migrations |
| `expected_clarifying_questions` | optional | Number / topics of clarifying questions agent SHOULD ask (senior judgment) |
| `expected_observability_hooks` | optional | List of hooks (log field, span name, metric counter) the answer MUST emit |
| `expected_handoff_reference` | optional | For handoff-benchmark cases: the CE7 reference path the agent MUST escalate to |
| `expected_self_review_items` | optional | Subset of Self-Review Checklist items the answer MUST surface (e.g., `idempotency`, `tenant_authz`) |
| `expected_production_readiness` | optional | Boolean — true if answer MUST include the Production Readiness Mini-Bar block |

## Scoring (per task, total 100)

### Deterministic dimensions (60 pts) — auto-graded by `run_eval.py`

| Dimension | Points | Pass criterion |
|---|---|---|
| **Routing** | 15 | Agent invokes `expected_pack` AND any `expected_references` |
| **Inclusion** | 15 | Every entry in `must_include` appears at least once in the response |
| **Exclusion** | 15 | No entry in `must_not_include` appears |
| **Test present** | 10 | Response contains a runnable test (matched by framework signature) |
| **Compiles** | 5 | Code blocks pass language-specific lint/syntax check (best-effort) |

### Senior-judgment dimensions (40 pts) — LLM-judge or manual review

| Dimension | Points | Pass criterion |
|---|---|---|
| **Clarify-quality** | 5 | Asked the right clarifying questions (Clarify-First lenses) OR explicitly stated assumptions when none were needed. No fluff/stylistic questions. |
| **Trade-off articulation** | 5 | Named at least one rejected alternative with reason when the task involved a non-trivial choice. |
| **Security depth** | 10 | Resource-level authz, parameterized queries, no secrets, framework primitives — all visible in code, not just claimed. For security tasks, exploit path explained. |
| **Observability hooks** | 5 | For new endpoint/job/consumer: structured log w/ `correlation_id`, OTel span name, metric counter. Matches `expected_observability_hooks` if specified. |
| **Release safety** | 5 | For risky changes: feature flag OR expand-contract OR explicit single-deploy-revert path. Rollback method named. |
| **Handoff to CE7** | 10 | For tasks that exceed Coding's authority (`handoff-benchmark.jsonl`): agent escalates to the correct `expected_handoff_reference` and produces an Implementation Input Package per `HANDOFF-PROTOCOL.md`. For tasks that do NOT need handoff: agent does NOT spuriously escalate. |

### Pass thresholds

- **Per task**: 75/100 AND no explicit syntax-check failure (`compiles=false`).
- **Critical security/data-loss tasks**: 90/100 AND `Security depth` ≥ 8 AND `Exclusion` = 15.
- **Suite**: ≥ 90% of tasks pass AND 0 critical tasks fail AND ≥ 80% of `handoff-benchmark` cases route correctly.

Skipped syntax checks do not fail snippets because many agent responses contain partial examples rather than complete projects.

## Critical Tasks (must pass — security/data-loss)

- `code-024` migration safety
- `code-001`, `code-011` parameterized queries
- `code-017`, `code-018` secure storage (no UserDefaults/SharedPrefs leak)
- `code-029` tenant-scoped resource authorization (IDOR regression)
- `handoff-001` through `handoff-005` (escalation correctness)

## Three benchmark suites

| Suite | File | Purpose |
|---|---|---|
| **Coding** | `coding-benchmark.jsonl` | Implementation tasks across 10 packs / 10 languages. Default suite. |
| **Handoff** | `handoff-benchmark.jsonl` | Tasks that intentionally exceed Coding's authority. Tests escalation correctness. |
| **Anti-pattern** | `anti-pattern-benchmark.jsonl` | Tasks where the agent must NOT produce a known wrong pattern (string-concat SQL, Thread.sleep in test, route-only authz, secrets in env-files, etc). |
| **Debugging** | `debugging-benchmark.jsonl` | Bug-investigation flow (evidence -> hypothesis -> root cause -> fix). |
| **TDD** | `tdd-benchmark.jsonl` | Test-first cycle (red -> green -> refactor) discipline. |

## Running

```bash
# Coding benchmark
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$(date +%Y%m%d)/coding-responses.jsonl \
  --report   runs/$(date +%Y%m%d)/coding-report.json

# Handoff benchmark
python evals/run_eval.py \
  --benchmark evals/handoff-benchmark.jsonl \
  --responses runs/$(date +%Y%m%d)/handoff-responses.jsonl \
  --report   runs/$(date +%Y%m%d)/handoff-report.json

# Anti-pattern benchmark
python evals/run_eval.py \
  --benchmark evals/anti-pattern-benchmark.jsonl \
  --responses runs/$(date +%Y%m%d)/anti-responses.jsonl \
  --report   runs/$(date +%Y%m%d)/anti-report.json
```

`responses.jsonl` is produced by piping each prompt through your agent runner; one line per task with shape:

```json
{"id": "code-001", "response": "<agent's full markdown reply>", "packs_invoked": ["backend-pack"], "references_invoked": ["java-spring-boot"]}
```

For senior-judgment dimensions (40 pts), pipe responses through an LLM judge with this prompt template:

```
You are an expert engineering reviewer. Score the agent response against the rubric below (0-N per dimension).
Return JSON: {"clarify_quality": <0-5>, "tradeoff": <0-5>, "security_depth": <0-10>, "observability": <0-5>, "release_safety": <0-5>, "handoff": <0-10>, "rationale": "<1-3 sentences>"}.
Rubric: <paste senior-judgment table above>.
Task: <prompt>.
Response: <agent response>.
```

## CI Integration (GitHub Actions)

```yaml
- name: Run agent eval suite
  run: |
    python evals/run_eval.py \
      --benchmark evals/coding-benchmark.jsonl \
      --responses runs/${{ github.sha }}/responses.jsonl \
      --report   runs/${{ github.sha }}/report.json \
      --fail-under 90 \
      --critical-must-pass code-024,code-001,code-011,code-017,code-018,code-029
    python evals/run_eval.py \
      --benchmark evals/handoff-benchmark.jsonl \
      --responses runs/${{ github.sha }}/handoff-responses.jsonl \
      --report   runs/${{ github.sha }}/handoff-report.json \
      --fail-under 80
```

Exit code: 0 if pass-rate >= `--fail-under` AND all `--critical-must-pass` pass, else non-zero -> blocks merge.

## Adding a New Task

1. Append JSONL line to the appropriate suite (`coding-benchmark.jsonl`, `handoff-benchmark.jsonl`, `anti-pattern-benchmark.jsonl`).
2. Choose `must_include` to cover the **non-obvious correct pattern** (e.g., `CONCURRENTLY` for online index).
3. Choose `must_not_include` to catch **the most common wrong answer** (e.g., `String sql = "..." + input`).
4. For senior-judgment tasks, populate `expected_clarifying_questions`, `expected_observability_hooks`, `expected_handoff_reference`, `expected_self_review_items`, `expected_production_readiness` as applicable.
5. If task has security implications, add its id to "Critical Tasks" above.
6. Run `python evals/run_eval.py --benchmark ... --responses ... --dry-run` to validate JSONL shape.
7. Run `python evals/validate-references.py` to verify pack <-> reference consistency.
8. Run `python scripts/validate_packs.py` to verify the pack layout still passes.

## Benchmark Coverage Matrix

Current coverage of `coding-benchmark.jsonl` across packs and languages (updated when new tasks are added):

| Pack | Tasks | Languages covered |
|---|---|---|
| `backend-pack` | code-001..004, 011..015 (9) | Java, C#, Python, TS, Go, Rust, Kotlin |
| `frontend-pack` | code-005..007 (3) | TypeScript |
| `mobile-pack` | code-016..018 (3) | Dart, Swift, Kotlin |
| `database-pack` | code-010, 024 (2) | TypeScript, SQL |
| `api-design-pack` | code-019..021 (3) | YAML, TypeScript, Proto |
| `observability-pack` | code-022, 023 (2) | Python, Go |
| `testing-pack` | code-026 (1, plus test-present scoring across coding tasks) | Java |
| `debugging-pack` | code-027 (1, plus separate `debugging-benchmark.jsonl`) | Python/prose diagnostics |
| `devops-pack` | code-008, 009, 028 (3) | Dockerfile, YAML, TypeScript/AWS CDK |
| `quality-pack` | code-025, 029 (2) | TypeScript |

**Coverage gaps to address in future evals:**
- Add dedicated tasks for `observability-pack` in Java/.NET/Node, not only Python/Go.
- Add mobile E2E tasks (Detox/Maestro/XCUITest/Espresso), not only unit/widget tests.
- Add data-loss recovery / rollback drills for destructive migrations.
- Add senior-judgment tasks (ambiguous spec triggering Clarify-First; perf trade-off articulation).
- Add release-safety tasks (rollout%/kill-switch/SLO-gate).
