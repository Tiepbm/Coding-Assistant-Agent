#!/usr/bin/env bash
# Dual-agent Routing Guard Hook
# Warns/blocks Coding Assistant when a tool call appears to perform a CE7-owned decision.

set -euo pipefail

if [[ "${SKIP_ROUTING_GUARD:-}" == "true" ]]; then
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

INPUT="$(cat)"
MODE="${ROUTING_GUARD_MODE:-${GUARD_MODE:-warn}}"
ACTIVE="${ACTIVE_AGENT:-auto}"
LOG_DIR="${ROUTING_GUARD_LOG_DIR:-logs/copilot/routing-guard}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/routing.log"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])' 2>/dev/null || \
    sed 's/\\/\\\\/g; s/"/\\"/g'
}

extract_payload() {
  python3 - "$INPUT" <<'PY' 2>/dev/null || true
import json, os, sys
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
parts = [tool_name, raw]
if isinstance(tool_args, str):
    parts.append(tool_args)
    try:
        parsed_args = json.loads(tool_args)
        parts.extend(flatten(parsed_args))
    except Exception:
        pass
else:
    parts.extend(flatten(tool_args))
parts.extend(flatten(tool_input))
print(tool_name)
print(" ".join(p for p in parts if p))
PY
}

infer_active_agent() {
  local active="$1"
  local text="$2"
  if [[ "$active" != "auto" ]]; then
    printf '%s\n' "$active"
    return 0
  fi
  case "$(basename "$(pwd)")" in
    coding-assistant-agent) printf 'coding\n'; return 0 ;;
    software-engineering-agent) printf 'ce7\n'; return 0 ;;
  esac
  if printf '%s\n' "$text" | grep -qiE 'coding-assistant|Coding Assistant|@coding-assistant'; then
    printf 'coding\n'
  elif printf '%s\n' "$text" | grep -qiE 'ce7-software-engineering|CE7 Software Engineering|@ce7-software-engineering'; then
    printf 'ce7\n'
  else
    printf 'unknown\n'
  fi
}

EXTRACTED="$(extract_payload)"
TOOL_NAME="$(printf '%s\n' "$EXTRACTED" | sed -n '1p')"
COMBINED="$(printf '%s\n' "$EXTRACTED" | sed '1d')"
if [[ -z "$COMBINED" ]]; then
  COMBINED="$INPUT"
fi
RESOLVED_AGENT="$(infer_active_agent "$ACTIVE" "$COMBINED")"

# Only enforce Coding -> CE7 escalation. CE7 is allowed to discuss/produce decisions.
if [[ "$RESOLVED_AGENT" != "coding" ]]; then
  printf '{"timestamp":"%s","event":"routing_skipped","agent":"%s","tool":"%s"}\n' \
    "$TIMESTAMP" "$RESOLVED_AGENT" "$(printf '%s' "$TOOL_NAME" | json_escape)" >> "$LOG_FILE"
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

CE7_SIGNALS=(
  "affects[[:space:]].*(service|team|teams):::Task affects more than one service/team"
  "vendor[[:space:]].*(selection|choice|choose|pick):::Vendor or engine selection is CE7-owned"
  "(SLO|SLI|error[[:space:]_-]*budget|alert[[:space:]_-]*threshold):::SLO/SLI/error-budget/alert threshold is CE7-owned"
  "public[[:space:]].*API.*(version|versioning|breaking|governance):::Public API versioning/breaking-change governance is CE7-owned"
  "multi[[:space:]_-]*tenant.*(isolation|strategy|boundary):::Multi-tenant isolation strategy is CE7-owned"
  "data[[:space:]_-]*residency|regulatory[[:space:]_-]*class|compliance[[:space:]_-]*class:::Regulatory classification/data residency is CE7-owned"
  "resilience[[:space:]_-]*pattern|circuit[[:space:]_-]*breaker[[:space:]_-]*policy|retry[[:space:]_-]*policy|bulkhead[[:space:]_-]*policy:::Resilience policy/pattern selection is CE7-owned"
  "caching[[:space:]_-]*strategy|cache.*source[[:space:]_-]*of[[:space:]_-]*truth|invalidation[[:space:]_-]*policy:::Caching strategy/source-of-truth decisions are CE7-owned"
  "outbox[[:space:]_-]*pattern|saga[[:space:]_-]*pattern|workflow[[:space:]_-]*pattern:::Outbox/saga/workflow pattern selection is CE7-owned"
  "search[[:space:]_-]*index.*(design|strategy|reindex|alias|authz):::Search index design/reindex strategy is CE7-owned"
  "object[[:space:]_-]*storage.*(retention|signed[[:space:]_-]*URL|scan[[:space:]_-]*policy):::Object storage retention/signed URL/scan policy is CE7-owned"
  "cannot[[:space:]].*reverse[[:space:]].*single[[:space:]_-]*deploy|irreversible|one[[:space:]_-]*way[[:space:]_-]*door:::Irreversible decision requires CE7"
  "incident[[:space:]_-]*response|postmortem[[:space:]_-]*owner|on[[:space:]_-]*call[[:space:]_-]*owner:::Incident process/ownership is CE7-owned"
  "capacity[[:space:]_-]*planning|FinOps|cost[[:space:]_-]*guardrail|cost[[:space:]_-]*ceiling:::Capacity/FinOps guardrails are CE7-owned"
)

MATCHED_SIGNAL=""
MATCHED_RULE=""
for entry in "${CE7_SIGNALS[@]}"; do
  regex="${entry%%:::*}"
  rule="${entry#*:::}"
  if printf '%s\n' "$COMBINED" | grep -qiE "$regex" 2>/dev/null; then
    MATCHED_SIGNAL="$(printf '%s\n' "$COMBINED" | grep -oiE "$regex" 2>/dev/null | head -1 || true)"
    MATCHED_RULE="$rule"
    break
  fi
done

if [[ -z "$MATCHED_SIGNAL" ]]; then
  printf '{"timestamp":"%s","event":"routing_passed","agent":"coding","tool":"%s"}\n' \
    "$TIMESTAMP" "$(printf '%s' "$TOOL_NAME" | json_escape)" >> "$LOG_FILE"
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

reason="Routing Guard: Coding Assistant hit CE7-level signal '${MATCHED_SIGNAL}'. Rule: ${MATCHED_RULE}. Per HANDOFF-PROTOCOL.md §2, escalate to @ce7-software-engineering or set SKIP_ROUTING_GUARD=true for reviewed exceptions."
printf '{"timestamp":"%s","event":"ce7_signal_detected","mode":"%s","agent":"coding","tool":"%s","signal":"%s","rule":"%s"}\n' \
  "$TIMESTAMP" "$MODE" "$(printf '%s' "$TOOL_NAME" | json_escape)" "$(printf '%s' "$MATCHED_SIGNAL" | json_escape)" "$(printf '%s' "$MATCHED_RULE" | json_escape)" >> "$LOG_FILE"

if [[ "$MODE" == "block" ]]; then
  printf '{"permissionDecision":"deny","permissionDecisionReason":"%s"}\n' "$(printf '%s' "$reason" | json_escape)"
else
  printf '%s\n' "$reason" >&2
  printf '{"permissionDecision":"allow"}\n'
fi

