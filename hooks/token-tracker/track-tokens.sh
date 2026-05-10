#!/usr/bin/env bash
# Dual-agent Token Tracker Hook
# Logs session activity and optional token budget verdicts at session end.

set -euo pipefail

[[ "${SKIP_TOKEN_TRACKER:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${TOKEN_TRACKER_LOG_DIR:-logs/copilot/tokens}"
REPORT_FILE="${TOKEN_USAGE_HISTORY:-reports/token-usage-history.jsonl}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR" "$(dirname "$REPORT_FILE")"
LOG_FILE="$LOG_DIR/usage.log"

files_modified=0
lines_added=0
lines_removed=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  files_modified="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
  while read -r added removed _path; do
    [[ -z "${added:-}" ]] && continue
    [[ "$added" =~ ^[0-9]+$ ]] && lines_added=$((lines_added + added))
    [[ "$removed" =~ ^[0-9]+$ ]] && lines_removed=$((lines_removed + removed))
  done < <(git diff --numstat HEAD 2>/dev/null || true)
fi

budget_verdict="UNKNOWN"
responses_file="${TOKEN_RESPONSES_FILE:-}"
if [[ -z "$responses_file" && -f runs/latest/responses.jsonl ]]; then
  responses_file="runs/latest/responses.jsonl"
fi
if [[ -n "$responses_file" && -f "$responses_file" && -f scripts/check_token_budgets.py ]]; then
  if python3 scripts/check_token_budgets.py "$responses_file" >/tmp/dual-agent-token-budget.out 2>&1; then
    budget_verdict="PASS"
  else
    budget_verdict="FAIL"
  fi
fi

estimated_cost_usd="${ESTIMATED_COST_USD:-0}"
entry="{\"timestamp\":\"$TIMESTAMP\",\"event\":\"token_usage_proxy\",\"files_modified\":$files_modified,\"lines_added\":$lines_added,\"lines_removed\":$lines_removed,\"budget_verdict\":\"$budget_verdict\",\"estimated_cost_usd\":$estimated_cost_usd}"
printf '%s\n' "$entry" >> "$LOG_FILE"
printf '%s\n' "$entry" >> "$REPORT_FILE"
exit 0

