#!/usr/bin/env bash
set -euo pipefail

[[ "${SKIP_LOGGING:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${SESSION_LOG_DIR:-logs/copilot/sessions}"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
AGENT="${ACTIVE_AGENT:-auto}"
printf '{"timestamp":"%s","event":"sessionStart","agent":"%s","cwd":"%s"}\n' \
  "$TIMESTAMP" "$AGENT" "$(pwd)" >> "$LOG_DIR/session.log"
exit 0

