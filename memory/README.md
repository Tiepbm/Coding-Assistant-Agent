# memory/

This folder is the agent's **learning surface**: a small, append-only corpus of:

- `learned-patterns.md` — patterns the agent has discovered (or had pointed out) during PR reviews and eval runs. Each entry: bug + fix + benchmark case ID.
- `routing-corrections.jsonl` — cases where the agent routed to the wrong pack/reference; recorded as JSONL with `{prompt, wrong_route, correct_route, fix_pr}`.
- `interaction-log.jsonl` — optional sampled log of real interactions (only for pattern-mining; do NOT include user PII).

The folder is **maintainer-curated**. The agent does not write here at runtime. Use it to drive the quarterly review described in `docs/evaluation-improvement-playbook.md`.

## Hygiene

- Keep `learned-patterns.md` ≤ 500 lines; promote stable patterns into pack guidance and remove from this file.
- Rotate `routing-corrections.jsonl` once per quarter (archive the previous file as `routing-corrections-YYYY-Q.jsonl`).
- Never include real customer data.
