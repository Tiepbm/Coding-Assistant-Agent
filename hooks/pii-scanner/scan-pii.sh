#!/usr/bin/env bash
# Dual-agent PII Scanner Hook
# Blocks likely real PII in tool inputs before it is written to code/logs/files.

set -euo pipefail

if [[ "${SKIP_PII_SCAN:-}" == "true" ]]; then
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

INPUT="$(cat)"
MODE="${PII_MODE:-block}"
LOG_DIR="${PII_LOG_DIR:-logs/copilot/pii-scanner}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pii.log"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])' 2>/dev/null || sed 's/\\/\\\\/g; s/"/\\"/g'
}

extract_payload() {
  python3 - "$INPUT" <<'PY' 2>/dev/null || true
import json, sys
raw = sys.argv[1]
try:
    payload = json.loads(raw) if raw.strip() else {}
except Exception:
    payload = {}

def flatten(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten(item))
        return out
    if isinstance(value, dict):
        out = []
        for key, val in value.items():
            out.append(str(key))
            out.extend(flatten(val))
        return out
    return [str(value)]

tool_name = payload.get("toolName") or payload.get("tool_name") or ""
tool_args = payload.get("toolArgs")
tool_input = payload.get("toolInput") or payload.get("tool_input") or ""
parts = [tool_name]
if isinstance(tool_args, str):
    parts.append(tool_args)
    try:
        parts.extend(flatten(json.loads(tool_args)))
    except Exception:
        pass
else:
    parts.extend(flatten(tool_args))
parts.extend(flatten(tool_input))
print(tool_name)
print(" ".join(p for p in parts if p))
PY
}

EXTRACTED="$(extract_payload)"
TOOL_NAME="$(printf '%s\n' "$EXTRACTED" | sed -n '1p')"
COMBINED="$(printf '%s\n' "$EXTRACTED" | sed '1d')"
[[ -z "$COMBINED" ]] && COMBINED="$INPUT"

# Skip low-risk tools unless payload clearly contains write/edit/bash-like fields.
if ! printf '%s\n' "$TOOL_NAME $COMBINED" | grep -qiE 'bash|write|edit|create|apply_patch|insert|file|content|command'; then
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

# Allow obvious placeholders and documentation/test markers.
if printf '%s\n' "$COMBINED" | grep -qiE 'example\.com|user@example\.com|0901234xxx|HD0{8,}|BT0{8,}|placeholder|dummy|fake|sample'; then
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

PII_PATTERNS=(
  "CMND_CCCD:::critical:::(^|[^0-9])[0-9]{9}([0-9]{3})?([^0-9]|$):::Replace with placeholder ID such as 000000000000"
  "PHONE_VN:::high:::(^|[^0-9])0[35789][0-9]{8}([^0-9]|$):::Replace with masked phone such as 0901234xxx"
  "EMAIL_REAL:::high:::[A-Za-z0-9._%+-]+@(gmail|yahoo|outlook|hotmail)\.[A-Za-z]{2,}:::Replace with user@example.com"
  "BANK_ACCOUNT:::critical:::(bank|account|stk|so tai khoan|số tài khoản)[^0-9]{0,20}[0-9]{10,16}:::Replace with placeholder account number"
  "POLICY_NUMBER:::high:::HD[0-9]{8,12}:::Replace with HD00000000"
  "CLAIM_NUMBER:::high:::BT[0-9]{8,12}:::Replace with BT00000000"
)

FINDINGS=()
for entry in "${PII_PATTERNS[@]}"; do
  name="${entry%%:::*}"
  rest="${entry#*:::}"
  severity="${rest%%:::*}"
  rest="${rest#*:::}"
  regex="${rest%%:::*}"
  suggestion="${rest#*:::}"
  if printf '%s\n' "$COMBINED" | grep -qiE "$regex" 2>/dev/null; then
    match="$(printf '%s\n' "$COMBINED" | grep -oiE "$regex" 2>/dev/null | head -1 | sed 's/^[^[:alnum:]]*//;s/[^[:alnum:]]*$//' || true)"
    FINDINGS+=("$name	$severity	$match	$suggestion")
  fi
done

if [[ ${#FINDINGS[@]} -eq 0 ]]; then
  printf '{"timestamp":"%s","event":"pii_scan_passed","tool":"%s"}\n' "$TIMESTAMP" "$(printf '%s' "$TOOL_NAME" | json_escape)" >> "$LOG_FILE"
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

first_finding="${FINDINGS[0]}"
IFS=$'\t' read -r first_name first_severity first_match first_suggestion <<< "$first_finding"
reason="PII Scanner detected ${first_severity} ${first_name}: ${first_match}. ${first_suggestion}. Do not write real customer/person data to code, logs, tests, or docs."
printf '{"timestamp":"%s","event":"pii_detected","mode":"%s","tool":"%s","finding_count":%d,"first_pattern":"%s"}\n' \
  "$TIMESTAMP" "$MODE" "$(printf '%s' "$TOOL_NAME" | json_escape)" "${#FINDINGS[@]}" "$first_name" >> "$LOG_FILE"

if [[ "$MODE" == "block" ]]; then
  printf '{"permissionDecision":"deny","permissionDecisionReason":"%s"}\n' "$(printf '%s' "$reason" | json_escape)"
else
  printf '%s\n' "$reason" >&2
  printf '{"permissionDecision":"allow"}\n'
fi

