# Hướng dẫn Pipeline — Chạy Benchmark End-to-End

Tài liệu này hướng dẫn chạy eval pipeline cho Coding Assistant Agent: từ sinh response đến tạo báo cáo chấm điểm.

## Tổng quan pipeline

```
prompts (evals/*.jsonl) -> agent runner -> responses.jsonl -> run_eval.py -> report.json -> CI gate
```

Ba suite benchmark chấm độc lập:

| Suite | File | Ngưỡng fail-under mặc định |
|---|---|---|
| Coding | `evals/coding-benchmark.jsonl` | 90 |
| Handoff | `evals/handoff-benchmark.jsonl` | 80 |
| Anti-pattern | `evals/anti-pattern-benchmark.jsonl` | 95 |

## Bước 1 — Sinh response

Chạy mỗi prompt qua agent runner (Copilot CLI, OpenAI Assistants API, runner riêng). Output 1 dòng/task:

```json
{"id": "code-001", "response": "<reply markdown đầy đủ>", "packs_invoked": ["backend-pack"], "references_invoked": ["java-spring-boot"]}
```

Lưu vào `runs/<sha>/responses.jsonl`.

Ví dụ với runner giả định:

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

## Bước 2 — Chấm dimension deterministic

```bash
python3 evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$SHA/responses.jsonl \
  --report   runs/$SHA/coding-report.json \
  --fail-under 90 \
  --critical-must-pass code-024,code-001,code-011,code-017,code-018,code-029
```

Exit 0 = pass, khác 0 = fail. Report có điểm theo từng task.

## Bước 3 — Chấm dimension senior-judgment (LLM judge)

40 điểm senior-judgment (clarify, trade-off, security depth, observability, release safety, handoff) chấm bằng LLM judge:

```bash
python3 evals/llm_judge.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$SHA/responses.jsonl \
  --rubric    evals/rubric.md \
  --judge-model gpt-4o-or-equivalent \
  --output    runs/$SHA/senior-judgment.json
```

(`llm_judge.py` dùng template prompt trong `evals/rubric.md`. Tự implement trong môi trường của bạn.)

## Bước 4 — Chạy handoff + anti-pattern suite

```bash
python3 evals/run_eval.py --benchmark evals/handoff-benchmark.jsonl \
  --responses runs/$SHA/handoff-responses.jsonl \
  --report   runs/$SHA/handoff-report.json --fail-under 80

python3 evals/run_eval.py --benchmark evals/anti-pattern-benchmark.jsonl \
  --responses runs/$SHA/anti-responses.jsonl \
  --report   runs/$SHA/anti-report.json --fail-under 95
```

## Bước 5 — Aggregate + đọc báo cáo

Khuyến nghị tạo `runs/<sha>/aggregate.md`:

```bash
python3 evals/aggregate.py runs/$SHA > runs/$SHA/aggregate.md
```

Đọc kỹ. Tìm: critical fail, regression so với run trước, case điểm thấp nhất, pack hay sai.

## Bước 6 — CI gate

Trong `.github/workflows/eval.yml`:

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

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Tất cả case fail Routing | Runner không truyền `packs_invoked` | Thêm vào schema output runner |
| Critical task `code-029` fail | Regression tenant authz | Re-check `quality-pack/security-coding` + `security-handoff` |
| Handoff suite < 80% | Agent không escalate | Review bảng `Expert Escalation` trong agent file; xác nhận CE7 reference path tồn tại |
| Điểm senior-judgment thấp | Prompt LLM judge cũ | Paste lại block senior-judgment từ `evals/rubric.md` |
