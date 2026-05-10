#!/usr/bin/env bash
set -euo pipefail

[[ "${SKIP_LOGGING:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${SESSION_LOG_DIR:-logs/copilot/sessions}"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
AGENT="${ACTIVE_AGENT:-auto}"
PROMPT_LEN="$(python3 - "$INPUT" <<'PY' 2>/dev/null || printf '0'
import json, sys
try:
    p = json.loads(sys.argv[1]) if sys.argv[1].strip() else {}
except Exception:
    p = {}
prompt = p.get('prompt') or p.get('userPrompt') or p.get('user_prompt') or p.get('message') or ''
print(len(prompt))
PY
)"
printf '{"timestamp":"%s","event":"userPromptSubmitted","agent":"%s","cwd":"%s","prompt_length":%s}\n' \
  "$TIMESTAMP" "$AGENT" "$(pwd)" "${PROMPT_LEN:-0}" >> "$LOG_DIR/prompts.log"
exit 0

