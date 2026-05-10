#!/usr/bin/env bash
# Dual-agent Tool Guardian Hook
# Blocks dangerous shell/tool operations before Copilot executes them.
# Copilot contract: read event JSON from stdin. For preToolUse, deny with:
#   {"permissionDecision":"deny","permissionDecisionReason":"..."}

set -euo pipefail

if [[ "${SKIP_TOOL_GUARD:-}" == "true" ]]; then
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

INPUT="$(cat)"
MODE="${TOOL_GUARD_MODE:-${GUARD_MODE:-block}}"
LOG_DIR="${TOOL_GUARD_LOG_DIR:-logs/copilot/tool-guardian}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/guard.log"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])' 2>/dev/null || \
    sed 's/\\/\\\\/g; s/"/\\"/g'
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

EXTRACTED="$(extract_payload)"
TOOL_NAME="$(printf '%s\n' "$EXTRACTED" | sed -n '1p')"
COMBINED="$(printf '%s\n' "$EXTRACTED" | sed '1d')"
if [[ -z "$COMBINED" ]]; then
  COMBINED="$INPUT"
fi

ALLOWLIST=()
if [[ -n "${TOOL_GUARD_ALLOWLIST:-}" ]]; then
  IFS=',' read -r -a ALLOWLIST <<< "$TOOL_GUARD_ALLOWLIST"
fi

is_allowlisted() {
  local text="$1"
  local pattern
  for pattern in "${ALLOWLIST[@]}"; do
    pattern="$(printf '%s' "$pattern" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [[ -z "$pattern" ]] && continue
    [[ "$text" == *"$pattern"* ]] && return 0
  done
  return 1
}

if [[ ${#ALLOWLIST[@]} -gt 0 ]] && is_allowlisted "$COMBINED"; then
  printf '{"timestamp":"%s","event":"guard_skipped","reason":"allowlisted","tool":"%s"}\n' \
    "$TIMESTAMP" "$(printf '%s' "$TOOL_NAME" | json_escape)" >> "$LOG_FILE"
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

PATTERNS=(
  "destructive_file_ops:::critical:::rm[[:space:]]+-rf[[:space:]]+/([[:space:]]|$):::Use targeted rm on a specific safe path instead of root"
  "destructive_file_ops:::critical:::rm[[:space:]]+-rf[[:space:]]+~:::Use targeted rm on a specific safe path instead of home"
  "destructive_file_ops:::critical:::rm[[:space:]]+-rf[[:space:]]+\.?($|[[:space:]]):::Do not recursively delete the current directory"
  "destructive_file_ops:::critical:::(rm|del|unlink).*\.env([^[:alnum:]_]|$):::Back up .env files and remove only intentional placeholders"
  "destructive_file_ops:::critical:::(rm|del|unlink).*\.git([^[:alnum:]_]|$):::Never delete .git; use git commands to manage repository state"
  "destructive_git_ops:::critical:::git[[:space:]]+push[[:space:]]+(-f|--force)([[:space:]].*)?(main|master):::Use --force-with-lease on a feature branch, never force-push main/master"
  "destructive_git_ops:::high:::git[[:space:]]+reset[[:space:]]+--hard:::Use git stash or git reset --soft unless destructive reset is explicitly reviewed"
  "destructive_git_ops:::high:::git[[:space:]]+clean[[:space:]]+-fd:::Run git clean -n first and review the files"
  "database_destruction:::critical:::DROP[[:space:]]+TABLE:::Use a reversible migration and backup/restore plan"
  "database_destruction:::critical:::DROP[[:space:]]+DATABASE:::Create and verify backups; avoid DROP DATABASE in agent sessions"
  "database_destruction:::critical:::TRUNCATE([[:space:]]+TABLE)?:::Use DELETE with scoped WHERE and a rollback/recovery plan"
  "database_destruction:::high:::DELETE[[:space:]]+FROM[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*;:::Add a WHERE clause or batch predicate before deleting rows"
  "permission_abuse:::high:::chmod[[:space:]]+(-R[[:space:]]+)?777:::Use least privilege, usually 755 for dirs and 644 for files"
  "network_exfiltration:::critical:::curl.*\|.*(bash|sh):::Download the script, review it, then execute explicitly"
  "network_exfiltration:::critical:::wget.*\|.*(bash|sh):::Download the script, review it, then execute explicitly"
  "network_exfiltration:::high:::curl.*--data.*@:::Review file contents before uploading with curl --data @file"
  "system_danger:::high:::(^|[[:space:]])sudo[[:space:]]:::Avoid sudo in agent sessions; use least privilege"
  "system_danger:::high:::npm[[:space:]]+publish:::Run npm publish --dry-run and require human release approval"
)

THREATS=()
for entry in "${PATTERNS[@]}"; do
  category="${entry%%:::*}"
  rest="${entry#*:::}"
  severity="${rest%%:::*}"
  rest="${rest#*:::}"
  regex="${rest%%:::*}"
  suggestion="${rest#*:::}"
  if printf '%s\n' "$COMBINED" | grep -qiE "$regex" 2>/dev/null; then
    match="$(printf '%s\n' "$COMBINED" | grep -oiE "$regex" 2>/dev/null | head -1 || true)"
    THREATS+=("$category	$severity	$match	$suggestion")
  fi
done

if [[ ${#THREATS[@]} -eq 0 ]]; then
  printf '{"timestamp":"%s","event":"guard_passed","mode":"%s","tool":"%s"}\n' \
    "$TIMESTAMP" "$MODE" "$(printf '%s' "$TOOL_NAME" | json_escape)" >> "$LOG_FILE"
  printf '{"permissionDecision":"allow"}\n'
  exit 0
fi

first_threat="${THREATS[0]}"
IFS=$'\t' read -r first_category first_severity first_match first_suggestion <<< "$first_threat"
reason="Tool Guardian blocked ${first_severity} ${first_category}: ${first_match}. ${first_suggestion}. Set SKIP_TOOL_GUARD=true only for reviewed, intentional operations."

findings_json="["
first=true
for threat in "${THREATS[@]}"; do
  IFS=$'\t' read -r category severity match suggestion <<< "$threat"
  $first || findings_json+=","
  first=false
  findings_json+="{\"category\":\"$(printf '%s' "$category" | json_escape)\",\"severity\":\"$(printf '%s' "$severity" | json_escape)\",\"match\":\"$(printf '%s' "$match" | json_escape)\",\"suggestion\":\"$(printf '%s' "$suggestion" | json_escape)\"}"
done
findings_json+="]"
printf '{"timestamp":"%s","event":"threats_detected","mode":"%s","tool":"%s","threat_count":%d,"threats":%s}\n' \
  "$TIMESTAMP" "$MODE" "$(printf '%s' "$TOOL_NAME" | json_escape)" "${#THREATS[@]}" "$findings_json" >> "$LOG_FILE"

if [[ "$MODE" == "block" ]]; then
  printf '{"permissionDecision":"deny","permissionDecisionReason":"%s"}\n' "$(printf '%s' "$reason" | json_escape)"
else
  printf 'Tool Guardian warning: %s\n' "$reason" >&2
  printf '{"permissionDecision":"allow"}\n'
fi

