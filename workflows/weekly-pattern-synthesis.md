---
name: "Weekly Pattern Synthesis"
description: "Synthesize learned routing and implementation patterns from dual-agent logs"
on:
  schedule: "weekly on Monday 09:00 UTC+7"
  workflow_dispatch: true
permissions:
  contents: write
  pull-requests: write
safe-outputs:
  create-pull-request:
    title-prefix: "[memory] "
    labels: [agent-improvement, automated]
---

# Weekly Pattern Synthesis

Analyze the past week of `memory/interaction-log.jsonl` and `logs/copilot/**` metadata for CE7 + Coding Assistant.

## Automatic memory maintenance (run first)

The Memory MCP captures interactions automatically (hook + tool). Recompute confidence and
snapshot accuracy so the synthesis works from fresh numbers:

```bash
python3 mcp-memory/memory_cli.py synthesize
python3 mcp-memory/memory_cli.py report --out reports/accuracy-history.jsonl
python3 mcp-memory/memory_cli.py export --out memory/learned-patterns.auto.md
python3 mcp-memory/memory_cli.py promote --out memory/learned-patterns.md --synthesize
```

`reports/accuracy-history.jsonl` gives the week-over-week routing-accuracy proxy + average
pattern confidence (the automatic scoring). `memory/learned-patterns.auto.md` is the machine
draft. `promote` appends a deduped **`## PROPOSED` block** to `memory/learned-patterns.md`
(stable patterns: frequency ≥ 3 & confidence ≥ 0.7; recurring corrections: ≥ 2x) — these are
the items the PR asks a human to review.

## Steps

1. Read `software-engineering-agent/memory/interaction-log.jsonl` and `coding-assistant-agent/memory/interaction-log.jsonl` entries from the last 7 days, plus `memory/learned-patterns.auto.md` and any new `## PROPOSED` block in `memory/learned-patterns.md`.
2. Identify recurring routing misses, handoff gaps, guardrail false positives, and common implementation corrections.
3. For each `## PROPOSED` item: either promote it into the curated section / pack `When NOT to Use` / Tie-Break rules, or delete it. Remove the `## PROPOSED` block once triaged.
4. Keep CE7 learned patterns under 50 lines and Coding learned patterns under 500 lines by promoting stable patterns into pack guidance.
5. Create a PR for human review; never push directly to main.

