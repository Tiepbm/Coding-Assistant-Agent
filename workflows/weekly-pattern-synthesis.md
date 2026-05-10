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

## Steps

1. Read `software-engineering-agent/memory/interaction-log.jsonl` and `coding-assistant-agent/memory/interaction-log.jsonl` entries from the last 7 days.
2. Identify recurring routing misses, handoff gaps, guardrail false positives, and common implementation corrections.
3. Update `memory/learned-patterns.md` only with high-signal, privacy-safe patterns.
4. Keep CE7 learned patterns under 50 lines and Coding learned patterns under 500 lines by promoting stable patterns into pack guidance.
5. Create a PR for human review; never push directly to main.

