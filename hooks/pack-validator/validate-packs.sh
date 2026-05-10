#!/usr/bin/env bash
# Warn-only structural validator for agent packages.
set -euo pipefail

[[ "${SKIP_PACK_VALIDATOR:-}" == "true" ]] && exit 0
LOG_DIR="${PACK_VALIDATOR_LOG_DIR:-logs/copilot/pack-validator}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/validator.log"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

changed="$(git diff --name-only HEAD 2>/dev/null || true)"
if ! printf '%s\n' "$changed" | grep -qE '^(skills|agents|instructions|evals|\.github/(skills|agents|instructions))/'; then
  printf '{"timestamp":"%s","event":"validator_skipped","reason":"no_agent_package_files_changed"}\n' "$TIMESTAMP" >> "$LOG_FILE"
  exit 0
fi

validator=""
if [[ -f scripts/validate_packs.py ]]; then
  validator="scripts/validate_packs.py"
elif [[ -f scripts/validate_hybrid_packs.py ]]; then
  validator="scripts/validate_hybrid_packs.py"
else
  printf '{"timestamp":"%s","event":"validator_skipped","reason":"no_validator_script"}\n' "$TIMESTAMP" >> "$LOG_FILE"
  exit 0
fi

output_file="$(mktemp)"
status=0
python3 "$validator" >"$output_file" 2>&1 || status=$?
summary="$(tail -20 "$output_file" | tr '\n' ' ' | sed 's/"/\\"/g')"
rm -f "$output_file"

if [[ $status -eq 0 ]]; then
  printf '{"timestamp":"%s","event":"validator_passed","validator":"%s"}\n' "$TIMESTAMP" "$validator" >> "$LOG_FILE"
else
  printf '{"timestamp":"%s","event":"validator_failed","validator":"%s","status":%d,"summary":"%s"}\n' "$TIMESTAMP" "$validator" "$status" "$summary" >> "$LOG_FILE"
  printf 'Pack validator warning: %s failed. Summary: %s\n' "$validator" "$summary" >&2
fi

# Warn-only: never block session end.
exit 0

