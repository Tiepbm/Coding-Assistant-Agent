#!/usr/bin/env bash
set -euo pipefail

[[ "${SKIP_LOGGING:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${SESSION_LOG_DIR:-logs/copilot/sessions}"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
AGENT="${ACTIVE_AGENT:-auto}"
files_modified=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  files_modified="$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
fi
printf '{"timestamp":"%s","event":"sessionEnd","agent":"%s","cwd":"%s","files_modified":%s}\n' \
  "$TIMESTAMP" "$AGENT" "$(pwd)" "$files_modified" >> "$LOG_DIR/session.log"
exit 0

