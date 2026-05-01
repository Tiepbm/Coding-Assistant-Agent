# Pipeline Guide — End-to-End Benchmark Execution

This guide walks through running the eval pipeline for the Coding Assistant Agent: from generating model responses to producing a scored report.

## Pipeline overview

```
prompts (evals/*.jsonl) -> agent runner -> responses.jsonl -> run_eval.py -> report.json -> CI gate
```

Three benchmark suites are scored independently:

| Suite | File | Default fail-under |
|---|---|---|
| Coding | `evals/coding-benchmark.jsonl` | 90 |
| Handoff | `evals/handoff-benchmark.jsonl` | 80 |
| Anti-pattern | `evals/anti-pattern-benchmark.jsonl` | 95 |

## Step 1 — Generate responses

Pipe each prompt through your agent runner (Copilot CLI, OpenAI Assistants API, your own runner). Output one line per task:

```json
{"id": "code-001", "response": "<full agent reply markdown>", "packs_invoked": ["backend-pack"], "references_invoked": ["java-spring-boot"]}
```

Save to `runs/<sha>/responses.jsonl`.

Example with a hypothetical runner:

```bash
SHA=$(git rev-parse --short HEAD)
mkdir -p runs/$SHA
while read -r line; do
  id=$(echo "$line" | jq -r .id)
  prompt=$(echo "$line" | jq -r .prompt)
  response=$(./scripts/agent-runner.sh --prompt "$prompt")
  echo "{\"id\":\"$id\",\"response\":$response}" >> runs/$SHA/responses.jsonl
done < evals/coding-benchmark.jsonl
```

## Step 2 — Score deterministic dimensions

```bash
python3 evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$SHA/responses.jsonl \
  --report   runs/$SHA/coding-report.json \
  --fail-under 90 \
  --critical-must-pass code-024,code-001,code-011,code-017,code-018,code-029
```

Exit code 0 = pass, non-zero = fail. The report contains per-task scores.

## Step 3 — Score senior-judgment dimensions (LLM judge)

The 40-pt senior-judgment block (clarify-quality, trade-off, security depth, observability, release safety, handoff) is scored by an LLM judge:

```bash
python3 evals/llm_judge.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$SHA/responses.jsonl \
  --rubric    evals/rubric.md \
  --judge-model gpt-4o-or-equivalent \
  --output    runs/$SHA/senior-judgment.json
```

(`llm_judge.py` is wired to the rubric template in `evals/rubric.md`. Implement once per environment; the prompt is in the rubric.)

## Step 4 — Run handoff + anti-pattern suites

```bash
python3 evals/run_eval.py --benchmark evals/handoff-benchmark.jsonl \
  --responses runs/$SHA/handoff-responses.jsonl \
  --report   runs/$SHA/handoff-report.json --fail-under 80

python3 evals/run_eval.py --benchmark evals/anti-pattern-benchmark.jsonl \
  --responses runs/$SHA/anti-responses.jsonl \
  --report   runs/$SHA/anti-report.json --fail-under 95
```

## Step 5 — Aggregate + open the report

A `runs/<sha>/aggregate.md` is recommended:

```bash
python3 evals/aggregate.py runs/$SHA > runs/$SHA/aggregate.md
```

Read it. Look for: critical failures, regressions vs the previous run, lowest-scoring cases, and packs that hot-spot.

## Step 6 — CI gate

In `.github/workflows/eval.yml`:

```yaml
name: Coding Assistant Eval
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Validate pack layout
        run: python3 scripts/validate_packs.py
      - name: Validate references
        run: python3 evals/validate-references.py
      - name: Coding suite
        run: python3 evals/run_eval.py --benchmark evals/coding-benchmark.jsonl ... --fail-under 90
      - name: Handoff suite
        run: python3 evals/run_eval.py --benchmark evals/handoff-benchmark.jsonl ... --fail-under 80
      - name: Anti-pattern suite
        run: python3 evals/run_eval.py --benchmark evals/anti-pattern-benchmark.jsonl ... --fail-under 95
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All cases fail Routing | Runner not propagating `packs_invoked` | Add to runner output schema |
| Critical task `code-029` fails | Tenant authz regression | Re-check `quality-pack/security-coding` + `security-handoff` |
| Handoff suite < 80% | Agent not escalating | Review `Expert Escalation` table in agent file; ensure CE7 reference paths exist |
| Senior-judgment scores low | LLM judge prompt outdated | Re-paste the senior-judgment block from `evals/rubric.md` |
