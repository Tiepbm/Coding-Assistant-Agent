#!/usr/bin/env bash
# Validate .handoffs package shape after handoff edits.

set -euo pipefail

[[ "${SKIP_HANDOFF_VALIDATOR:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${HANDOFF_VALIDATOR_LOG_DIR:-logs/copilot/handoff-validator}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/handoff.log"

json_string() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

payload_text="$(python3 - "$INPUT" <<'PY' 2>/dev/null || true
import json, sys
raw=sys.argv[1]
try: p=json.loads(raw) if raw.strip() else {}
except Exception: p={}
text=raw
args=p.get('toolArgs')
if isinstance(args,str):
    text += ' ' + args
else:
    text += ' ' + json.dumps(args)
print(text)
PY
)"

if ! printf '%s\n' "$payload_text" | grep -qE '\.handoffs/|handoff'; then
  # If active handoff exists, still validate at session/post hook time; otherwise skip.
  [[ -f .handoffs/.active ]] || exit 0
fi

errors=()
validate_input() {
  local file="$1"
  for key in adr_id title risk_class contract idempotency slo data_lifecycle security rollout runbook_stub on_call_owner; do
    grep -qE "^$key:" "$file" || errors+=("$file missing $key")
  done
}
validate_return() {
  local file="$1"
  for key in adr_id status files_touched production_readiness_mini_bar self_review_checklist residual_risks open_questions_for_ce7; do
    grep -qE "^$key:" "$file" || errors+=("$file missing $key")
  done
  status="$(grep -E '^status:' "$file" | head -1 | awk '{print $2}' | tr -d '"' || true)"
  case "$status" in implemented|partial|blocked) ;; *) errors+=("$file invalid status '$status'") ;; esac
}

if [[ -f .handoffs/.active ]]; then
  adr="$(tr -d '\r\n' < .handoffs/.active)"
  [[ -f ".handoffs/$adr/input-package.yaml" ]] && validate_input ".handoffs/$adr/input-package.yaml"
  [[ -f ".handoffs/$adr/return-package.yaml" ]] && validate_return ".handoffs/$adr/return-package.yaml"
else
  while IFS= read -r input_file; do validate_input "$input_file"; done < <(find .handoffs -path '*/input-package.yaml' -type f 2>/dev/null || true)
  while IFS= read -r return_file; do validate_return "$return_file"; done < <(find .handoffs -path '*/return-package.yaml' -type f 2>/dev/null || true)
fi

if [[ ${#errors[@]} -eq 0 ]]; then
  printf '{"timestamp":"%s","event":"handoff_validation_passed"}\n' "$TIMESTAMP" >> "$LOG_FILE"
  exit 0
fi

summary="$(printf '%s; ' "${errors[@]}")"
printf '{"timestamp":"%s","event":"handoff_validation_failed","error_count":%d,"summary":"%s"}\n' "$TIMESTAMP" "${#errors[@]}" "$(printf '%s' "$summary" | sed 's/"/\\"/g')" >> "$LOG_FILE"
encoded="$(printf '[dual-agent] Handoff validation warning: %s' "$summary" | json_string)"
printf '{"additionalContext":%s}\n' "$encoded"
exit 0

