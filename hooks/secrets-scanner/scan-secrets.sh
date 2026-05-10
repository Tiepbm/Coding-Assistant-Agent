#!/usr/bin/env bash
# Dual-agent Secrets Scanner Hook
# Scans changed files at session end for likely leaked credentials.

set -euo pipefail

[[ "${SKIP_SECRETS_SCAN:-}" == "true" ]] && exit 0
INPUT="$(cat)"
MODE="${SCAN_MODE:-warn}"
SCOPE="${SCAN_SCOPE:-diff}"
LOG_DIR="${SECRETS_LOG_DIR:-logs/copilot/secrets}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scan.log"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])' 2>/dev/null || sed 's/\\/\\\\/g; s/"/\\"/g'
}

should_skip_file() {
  local file="$1"
  case "$file" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.ico|*.pdf|*.zip|*.gz|*.tar|*.tgz|*.lock|package-lock.json|pnpm-lock.yaml|yarn.lock) return 0 ;;
    logs/*|node_modules/*|.git/*|dist/*|build/*|target/*|.next/*) return 0 ;;
  esac
  [[ ! -f "$file" ]] && return 0
  if command -v file >/dev/null 2>&1; then
    file "$file" | grep -qiE 'binary|image|compressed|archive' && return 0
  fi
  return 1
}

is_placeholder() {
  printf '%s\n' "$1" | grep -qiE 'example|changeme|change_me|your_|placeholder|dummy|fake|test|xxxxx|xxxx|000000|AKIAIOSFODNN7EXAMPLE'
}

collect_files() {
  if [[ -n "${SECRETS_SCAN_TARGETS:-}" ]]; then
    printf '%s\n' ${SECRETS_SCAN_TARGETS}
    return
  fi
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return
  fi
  if [[ "$SCOPE" == "staged" ]]; then
    git diff --cached --name-only --diff-filter=ACMRT 2>/dev/null || true
  else
    { git diff --name-only --diff-filter=ACMRT HEAD 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | sort -u
  fi
}

PATTERNS=(
  "AWS_ACCESS_KEY:::critical:::AKIA[0-9A-Z]{16}"
  "AWS_SECRET_KEY:::critical:::(aws_secret_access_key|AWS_SECRET_ACCESS_KEY)[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9/+=]{30,}"
  "GITHUB_PAT:::critical:::gh[pousr]_[A-Za-z0-9_]{30,}"
  "GITHUB_FINE_GRAINED_PAT:::critical:::github_pat_[A-Za-z0-9_]{30,}"
  "PRIVATE_KEY:::critical:::-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"
  "SLACK_TOKEN:::high:::xox[baprs]-[A-Za-z0-9-]{20,}"
  "STRIPE_SECRET_KEY:::critical:::sk_live_[A-Za-z0-9]{20,}"
  "NPM_TOKEN:::high:::npm_[A-Za-z0-9]{20,}"
  "JWT_TOKEN:::medium:::eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
  "GENERIC_SECRET:::high:::(api[_-]?key|secret|password|passwd|token)[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9_./+=:-]{16,}"
  "CONNECTION_STRING:::high:::(postgres|postgresql|mysql|mongodb|redis|mssql)://[^[:space:]'\"]+:[^[:space:]'\"]+@"
  "INTERNAL_IP_PORT:::medium:::(10|172\.(1[6-9]|2[0-9]|3[0-1])|192\.168)\.[0-9]{1,3}\.[0-9]{1,3}:[0-9]{2,5}"
  "INSURANCE_PARTNER_KEY:::high:::(reinsurance|payment|claim|policy|psp|partner)[A-Za-z0-9_ -]{0,30}(key|secret|token)[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9_./+=:-]{16,}"
)

FINDINGS=()
files_scanned=0
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  should_skip_file "$file" && continue
  files_scanned=$((files_scanned + 1))
  line_no=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line_no=$((line_no + 1))
    for entry in "${PATTERNS[@]}"; do
      name="${entry%%:::*}"
      rest="${entry#*:::}"
      severity="${rest%%:::*}"
      regex="${rest#*:::}"
      if printf '%s\n' "$line" | grep -qE "$regex" 2>/dev/null; then
        match="$(printf '%s\n' "$line" | grep -oE "$regex" 2>/dev/null | head -1 || true)"
        is_placeholder "$match" && continue
        if [[ -n "${SECRETS_ALLOWLIST:-}" ]] && printf '%s\n' "$match $file" | grep -qE "$SECRETS_ALLOWLIST"; then
          continue
        fi
        redacted="$(printf '%s' "$match" | cut -c1-8)***"
        FINDINGS+=("$file	$line_no	$name	$severity	$redacted")
      fi
    done
  done < "$file"
done < <(collect_files)

if [[ ${#FINDINGS[@]} -eq 0 ]]; then
  printf '{"timestamp":"%s","event":"scan_complete","mode":"%s","scope":"%s","status":"clean","files_scanned":%d}\n' "$TIMESTAMP" "$MODE" "$SCOPE" "$files_scanned" >> "$LOG_FILE"
  exit 0
fi

first="${FINDINGS[0]}"
IFS=$'\t' read -r first_file first_line first_name first_severity first_redacted <<< "$first"
reason="Secrets Scanner found ${#FINDINGS[@]} potential secret(s); first: ${first_name} ${first_severity} at ${first_file}:${first_line}. Remove or replace with env/vault references."
printf '{"timestamp":"%s","event":"secrets_found","mode":"%s","scope":"%s","files_scanned":%d,"finding_count":%d,"first_file":"%s","first_pattern":"%s"}\n' \
  "$TIMESTAMP" "$MODE" "$SCOPE" "$files_scanned" "${#FINDINGS[@]}" "$(printf '%s' "$first_file" | json_escape)" "$first_name" >> "$LOG_FILE"

printf '%s\n' "$reason" >&2
if [[ "$MODE" == "block" ]]; then
  exit 1
fi
exit 0

