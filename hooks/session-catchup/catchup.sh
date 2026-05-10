#!/usr/bin/env bash
# Session-start handoff state catchup.

set -euo pipefail

[[ "${SKIP_SESSION_CATCHUP:-}" == "true" ]] && exit 0
INPUT="$(cat)"

json_string() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

if [[ ! -f .handoffs/.active ]]; then
  exit 0
fi
ADR_ID="$(tr -d '\r\n' < .handoffs/.active)"
DIR=".handoffs/$ADR_ID"
[[ -z "$ADR_ID" || ! -d "$DIR" ]] && exit 0

changed=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  changed="$(git diff --stat HEAD 2>/dev/null | tail -20 || true)"
fi

context="[dual-agent session catchup]
Active ADR: $ADR_ID
Directory: $DIR
"
[[ -f "$DIR/progress.md" ]] && context+="
Recent progress:
$(tail -n 25 "$DIR/progress.md")
"
[[ -f "$DIR/return-package.yaml" ]] && context+="
Return package status:
$(grep -E '^(status|adr_id):' "$DIR/return-package.yaml" || true)
"
[[ -n "$changed" ]] && context+="
Uncommitted diff stat:
$changed
"
context+="
Reboot check: Which agent am I? What ADR is active? What is done? What remains? Are there CE7 re-engagement triggers?"
encoded="$(printf '%s' "$context" | json_string)"
printf '{"additionalContext":%s}\n' "$encoded"

