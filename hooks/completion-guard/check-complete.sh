#!/usr/bin/env bash
# Completion guard for active handoffs.

set -euo pipefail

[[ "${SKIP_COMPLETION_GUARD:-}" == "true" ]] && exit 0
INPUT="$(cat)"
MODE="${COMPLETION_GUARD_MODE:-warn}"
ACTIVE="${ACTIVE_AGENT:-auto}"

if [[ ! -f .handoffs/.active ]]; then
  exit 0
fi
ADR_ID="$(tr -d '\r\n' < .handoffs/.active)"
DIR=".handoffs/$ADR_ID"
[[ -z "$ADR_ID" || ! -d "$DIR" ]] && exit 0

fail_or_warn() {
  local msg="$1"
  if [[ "$MODE" == "block" ]]; then
    echo "$msg" >&2
    exit 1
  fi
  encoded="$(printf '%s' "$msg" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$msg")"
  printf '{"additionalContext":%s}\n' "$encoded"
  exit 0
}

if [[ "$ACTIVE" == "ce7" ]]; then
  input="$DIR/input-package.yaml"
  [[ -f "$input" ]] || fail_or_warn "[dual-agent] CE7 handoff $ADR_ID incomplete: missing input-package.yaml. Create it from HANDOFF-PROTOCOL.md §3 or clear .handoffs/.active."
  missing=()
  for key in adr_id title risk_class contract rollout runbook_stub on_call_owner; do
    grep -qE "^$key:" "$input" || missing+=("$key")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    fail_or_warn "[dual-agent] CE7 input package $ADR_ID missing required fields: ${missing[*]}."
  fi
  exit 0
fi

# Coding/default: require return package to exist and status to be implemented/partial/blocked.
return_pkg="$DIR/return-package.yaml"
[[ -f "$return_pkg" ]] || fail_or_warn "[dual-agent] Coding handoff $ADR_ID incomplete: missing return-package.yaml Self-Review Block. Continue working or create return-package.yaml with status: partial/blocked."
status="$(grep -E '^status:' "$return_pkg" | head -1 | awk '{print $2}' | tr -d '"' || true)"
case "$status" in
  implemented|partial|blocked) ;;
  *) fail_or_warn "[dual-agent] Coding handoff $ADR_ID has invalid/missing return-package status '$status'. Use implemented | partial | blocked." ;;
esac

if [[ "$status" == "implemented" ]]; then
  for required in production_readiness_mini_bar self_review_checklist residual_risks open_questions_for_ce7; do
    grep -qE "^$required:" "$return_pkg" || fail_or_warn "[dual-agent] return-package.yaml for $ADR_ID missing $required. Complete Self-Review before stopping."
  done
fi
exit 0

