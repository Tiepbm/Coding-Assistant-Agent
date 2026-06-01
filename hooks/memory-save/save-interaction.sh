#!/usr/bin/env bash
# Privacy-safe interaction metadata save.

set -euo pipefail

[[ "${SKIP_MEMORY_SAVE:-}" == "true" ]] && exit 0
INPUT="$(cat)"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TARGET="${MEMORY_LOG_FILE:-memory/interaction-log.jsonl}"
if [[ ! -d "$(dirname "$TARGET")" ]]; then
  TARGET="logs/copilot/memory/interaction-log.jsonl"
fi
mkdir -p "$(dirname "$TARGET")"

json_array_from_lines() {
  python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))'
}

files=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  files="$(git diff --name-only HEAD 2>/dev/null || true)"
fi
files_json="$(printf '%s\n' "$files" | json_array_from_lines)"

packs_json="$(FILES_FOR_PACKS="$files" python3 - <<'PY'
import json, os, re
packs = set()
for path in [line.strip() for line in os.environ.get('FILES_FOR_PACKS', '').splitlines() if line.strip()]:
    parts = path.split('/')
    if 'skills' in parts:
        idx = parts.index('skills')
        if idx + 1 < len(parts):
            packs.add(parts[idx + 1])
    low = path.lower()
    if re.search(r'backend|controller|service|repository|src/main|src/test', low): packs.add('backend-pack')
    if re.search(r'frontend|components|pages|app/|src/app', low): packs.add('frontend-pack')
    if re.search(r'migration|db/|sql', low): packs.add('database-pack')
    if re.search(r'test|spec|e2e', low): packs.add('testing-pack')
    if re.search(r'docker|terraform|\.github/workflows|ci', low): packs.add('devops-pack')
    if re.search(r'logging|metrics|tracing|otel|runbook', low): packs.add('observability-pack')
print(json.dumps(sorted(packs)))
PY
)"

adr=""
status="none"
if [[ -f .handoffs/.active ]]; then
  adr="$(tr -d '\r\n' < .handoffs/.active)"
  [[ -f ".handoffs/$adr/return-package.yaml" ]] && status="$(grep -E '^status:' ".handoffs/$adr/return-package.yaml" | head -1 | awk '{print $2}' || echo active)"
  [[ "$status" == "none" ]] && status="active"
fi

python3 - "$TARGET" "$TIMESTAMP" "$files_json" "$packs_json" "$adr" "$status" <<'PY'
import json, sys
path, ts, files_json, packs_json, adr, status = sys.argv[1:]
entry = {
    "timestamp": ts,
    "event": "session_summary_proxy",
    "session_summary": "Privacy-safe session metadata from hook; no prompt/body stored",
    "files_touched": json.loads(files_json),
    "packs_likely": json.loads(packs_json),
    "active_adr": adr or None,
    "handoff_status": status,
    "quality": "unreviewed",
}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY

# --- Automatic capture into the Memory DB (no model needed) ---
# Soft-fail: never break a session if Python/CLI/DB is unavailable.
# Use only authoritative packs (from skills/<pack>/ paths) to avoid cross-agent label noise.
if [[ -f mcp-memory/memory_cli.py ]]; then
  packs_csv="$(FILES_FOR_PACKS="$files" python3 - <<'PY'
import os, re
packs = []
for path in [l.strip() for l in os.environ.get('FILES_FOR_PACKS','').splitlines() if l.strip()]:
    m = re.search(r'(?:^|/)skills/([^/]+)/', path)
    if m and m.group(1) not in packs:
        packs.append(m.group(1))
print(",".join(packs))
PY
)"
  n_files="$(printf '%s\n' "$files" | grep -c . || true)"
  if [[ "${n_files:-0}" -gt 0 ]]; then
    summary="auto session: ${n_files:-0} files${packs_csv:+, packs: $packs_csv}"
    MEMORY_AGENT="${ACTIVE_AGENT:-coding}" python3 mcp-memory/memory_cli.py record-outcome \
      --summary "$summary" \
      --packs "${packs_csv:-}" \
      --risk "${status:-none}" \
      --outcome auto \
      --source hook >/dev/null 2>&1 || true
  fi
fi

exit 0

