---
name: "Eval Regression Check"
description: "Run dual-agent eval suites and report score regressions"
on:
  schedule: "weekly on Friday 17:00 UTC+7"
  workflow_dispatch: true
permissions:
  contents: read
  issues: write
safe-outputs:
  create-issue:
    title-prefix: "[eval-regression] "
    labels: [regression, agent-quality]
---

# Eval Regression Check

Run structural and benchmark checks for CE7 + Coding Assistant.

## Steps

1. In `software-engineering-agent`, run `python3 scripts/validate_hybrid_packs.py` and `CHECK_GITHUB_MIRROR=1 python3 scripts/validate_hybrid_packs.py`.
2. In `coding-assistant-agent`, run `python3 scripts/validate_packs.py` and `python3 evals/validate-references.py`.
3. If benchmark response files are available, run CE7 `scripts/benchmark_pipeline.py score` and Coding `evals/run_eval.py`.
4. Compare with the latest report/baseline. Treat >5% score drop or a new critical-task failure as regression.
5. Create one issue with affected tasks, packs, references, and suggested owner.

