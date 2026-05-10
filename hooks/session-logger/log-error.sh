#!/usr/bin/env bash
set -euo pipefail

[[ "${SKIP_LOGGING:-}" == "true" ]] && exit 0
INPUT="$(cat)"
LOG_DIR="${SESSION_LOG_DIR:-logs/copilot/sessions}"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
AGENT="${ACTIVE_AGENT:-auto}"
PAYLOAD_SIZE="$(printf '%s' "$INPUT" | wc -c | tr -d ' ')"
printf '{"timestamp":"%s","event":"errorOccurred","agent":"%s","cwd":"%s","payload_bytes":%s}\n' \
  "$TIMESTAMP" "$AGENT" "$(pwd)" "$PAYLOAD_SIZE" >> "$LOG_DIR/errors.log"
exit 0

