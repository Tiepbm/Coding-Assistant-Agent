---
name: "Weekly Token Usage Report"
description: "Summarize token/work proxy metrics from dual-agent Copilot sessions"
on:
  schedule: "weekly on Monday 08:00 UTC+7"
  workflow_dispatch: true
permissions:
  contents: read
  issues: write
safe-outputs:
  create-issue:
    title-prefix: "[token-report] "
    labels: [metrics, cost]
---

# Weekly Token Usage Report

Aggregate `reports/token-usage-history.jsonl` and `logs/copilot/tokens/usage.log` from the past week.

## Include

- Total sessions observed.
- Files modified, lines added, lines removed.
- Budget verdict counts: PASS / FAIL / UNKNOWN.
- Estimated cost when present.
- Most expensive/high-churn sessions.
- Suggested pack/reference trims if token budget failures repeat.

