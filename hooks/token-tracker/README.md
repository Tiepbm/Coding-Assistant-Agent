# Token Tracker

`sessionEnd` hook that records a lightweight cost/work proxy.

It logs changed-file count, added/removed lines, optional budget verdict, and optional estimated cost. If `TOKEN_RESPONSES_FILE` points to a responses JSONL and `scripts/check_token_budgets.py` exists, the hook runs it.

## Environment

- `SKIP_TOKEN_TRACKER=true`
- `TOKEN_RESPONSES_FILE=runs/latest/responses.jsonl`
- `TOKEN_TRACKER_LOG_DIR=logs/copilot/tokens`
- `TOKEN_USAGE_HISTORY=reports/token-usage-history.jsonl`
- `ESTIMATED_COST_USD=0.15`

