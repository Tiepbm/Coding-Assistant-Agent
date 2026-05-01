# Eval Rubric — Coding Assistant

Each task in `evals/*.jsonl` is graded by `run_eval.py` against the agent's response.

## Schema (per JSONL line)

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Unique identifier (`code-001`) |
| `prompt` | yes | Verbatim user prompt sent to the agent |
| `expected_pack` | yes | Pack the agent must route to (e.g., `backend-pack`) |
| `expected_references` | yes | Reference file(s) the agent must consult |
| `language` | yes | Primary code language of the answer |
| `must_include` | optional | Substrings/symbols that MUST appear in code blocks |
| `must_not_include` | optional | Substrings that MUST NOT appear (anti-patterns) |
| `expected_test_framework` | optional | Test framework expected in answer |
| `expected_steps` | optional | Min number of distinct deploy/code steps for migrations |

## Scoring (per task, total 100)

| Dimension | Points | Pass criterion |
|---|---|---|
| **Routing** | 20 | Agent invokes `expected_pack` AND any `expected_references` |
| **Inclusion** | 30 | Every entry in `must_include` appears at least once in the response |
| **Exclusion** | 20 | No entry in `must_not_include` appears |
| **Test present** | 15 | Response contains a runnable test (matched by framework signature) |
| **Compiles** | 15 | Code blocks pass language-specific lint/syntax check (best-effort) |

Pass threshold per task: **75/100** AND no explicit syntax-check failure (`compiles=false`). Skipped syntax checks do not fail snippets because many agent responses contain partial examples rather than complete projects.

Suite pass threshold: **≥ 90 % of tasks pass** AND **0 critical (security/data-loss) tasks fail**.

## Critical Tasks (must pass — security/data-loss)

- `code-024` migration safety
- `code-001`, `code-011` parameterized queries
- `code-017`, `code-018` secure storage (no UserDefaults/SharedPrefs leak)
- `code-029` tenant-scoped resource authorization (IDOR regression)

## Running

```bash
python evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$(date +%Y%m%d)/responses.jsonl \
  --report   runs/$(date +%Y%m%d)/report.json
```

`responses.jsonl` is produced by piping each prompt through your agent runner; one line per task with shape:

```json
{"id": "code-001", "response": "<agent's full markdown reply>", "packs_invoked": ["backend-pack"], "references_invoked": ["java-spring-boot"]}
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
```

Exit code: 0 if pass-rate ≥ `--fail-under` AND all `--critical-must-pass` pass, else non-zero → blocks merge.

## Adding a New Task

1. Append JSONL line to `evals/coding-benchmark.jsonl` (or `debugging-benchmark.jsonl`, `tdd-benchmark.jsonl`).
2. Choose `must_include` to cover the **non-obvious correct pattern** (e.g., `CONCURRENTLY` for online index).
3. Choose `must_not_include` to catch **the most common wrong answer** (e.g., `String sql = "..." + input`).
4. If task has security implications, add its id to "Critical Tasks" above.
5. Run `python evals/run_eval.py --benchmark ... --responses ... --dry-run` to validate JSONL shape.
6. Run `python evals/validate-references.py` to verify pack ↔ reference consistency.

## Benchmark Coverage Matrix

Current coverage of `coding-benchmark.jsonl` (29 tasks) across packs and languages:

| Pack | Tasks | Languages covered |
|---|---|---|
| `backend-pack` | code-001, 002, 003, 004, 011, 012, 013, 014, 015 (9) | Java, C#, Python, TS, Go, Rust, Kotlin |
| `frontend-pack` | code-005, 006, 007 (3) | TypeScript |
| `mobile-pack` | code-016, 017, 018 (3) | Dart, Swift, Kotlin |
| `database-pack` | code-010, 024 (2) | TypeScript, SQL |
| `api-design-pack` | code-019, 020, 021 (3) | YAML, TypeScript, Proto |
| `observability-pack` | code-022, 023 (2) | Python, Go |
| `testing-pack` | code-026 (1, plus test-present scoring across coding tasks) | Java |
| `debugging-pack` | code-027 (1, plus separate `debugging-benchmark.jsonl`) | Python/prose diagnostics |
| `devops-pack` | code-008, 009, 028 (3) | Dockerfile, YAML, TypeScript/AWS CDK |
| `quality-pack` | code-025, 029 (2) | TypeScript |

**Coverage gaps to address in future evals:**
- Add dedicated tasks for `observability-pack` in Java/.NET/Node, not only Python/Go.
- Add mobile E2E tasks (Detox/Maestro/XCUITest/Espresso), not only unit/widget tests.
- Add data-loss recovery / rollback drills for destructive migrations.

