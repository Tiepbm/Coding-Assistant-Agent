#!/usr/bin/env bash
# Remind agents to update handoff progress/self-review after writes/edits.

set -euo pipefail

[[ "${SKIP_UPDATE_REMINDER:-}" == "true" ]] && exit 0
INPUT="$(cat)"

json_string() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

read_payload() {
  python3 - "$INPUT" <<'PY' 2>/dev/null || true
import json, sys
raw = sys.argv[1]
try: p = json.loads(raw) if raw.strip() else {}
except Exception: p = {}
tool = p.get('toolName') or p.get('tool_name') or ''
args = p.get('toolArgs')
text = raw
if isinstance(args, str):
    text += ' ' + args
    try: text += ' ' + json.dumps(json.loads(args))
    except Exception: pass
else:
    text += ' ' + json.dumps(args)
print(tool)
print(text)
PY
}

EXTRACTED="$(read_payload)"
TOOL_NAME="$(printf '%s\n' "$EXTRACTED" | sed -n '1p')"
TEXT="$(printf '%s\n' "$EXTRACTED" | sed '1d')"

if ! printf '%s %s\n' "$TOOL_NAME" "$TEXT" | grep -qiE 'write|edit|apply_patch|insert|bash|create'; then
  exit 0
fi

msg=""
if [[ -f .handoffs/.active ]]; then
  adr="$(tr -d '\r\n' < .handoffs/.active)"
  msg="[dual-agent] Active handoff $adr: after code/file changes, update .handoffs/$adr/progress.md. If implementation status changed, update .handoffs/$adr/return-package.yaml Self-Review Block."
elif printf '%s\n' "$TEXT" | grep -qE '(^|[ /])skills/|(^|[ /])agents/|(^|[ /])instructions/|(^|[ /])evals/|\.github/(skills|agents|instructions)'; then
  msg="[dual-agent] Agent package files changed. Run the repo validator and keep root skills/agents mirrored to .github/."
else
  exit 0
fi
encoded="$(printf '%s' "$msg" | json_string)"
printf '{"additionalContext":%s}\n' "$encoded"

