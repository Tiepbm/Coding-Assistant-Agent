#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
pass=0
fail=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export TOOL_GUARD_LOG_DIR="$TMP/logs/tool-guardian"
export ROUTING_GUARD_LOG_DIR="$TMP/logs/routing-guard"
export PII_LOG_DIR="$TMP/logs/pii-scanner"
export SECRETS_LOG_DIR="$TMP/logs/secrets"
export HANDOFF_VALIDATOR_LOG_DIR="$TMP/logs/handoff-validator"
export TOKEN_TRACKER_LOG_DIR="$TMP/logs/tokens"
export TOKEN_USAGE_HISTORY="$TMP/reports/token-usage-history.jsonl"

case_out() {
  local name="$1" expected="$2" cmd="$3" output
  if output="$(eval "$cmd" 2>&1)" && printf '%s' "$output" | grep -q "$expected"; then
    echo "PASS $name"; pass=$((pass+1))
  else
    echo "FAIL $name"; echo "$output"; fail=$((fail+1))
  fi
}
case_status() {
  local name="$1" status_expected="$2" expected="$3" cmd="$4" output status
  set +e; output="$(eval "$cmd" 2>&1)"; status=$?; set -e
  if [[ "$status" == "$status_expected" ]] && printf '%s' "$output" | grep -q "$expected"; then
    echo "PASS $name"; pass=$((pass+1))
  else
    echo "FAIL $name status=$status"; echo "$output"; fail=$((fail+1))
  fi
}
payload() { python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"toolName":"bash","toolArgs":json.dumps({"command":sys.argv[1]})}))
PY
}

safe="$(payload 'git status')"
rmrf="$(payload 'rm -rf /')"
force="$(payload 'git push --force origin main')"
drop="$(payload 'psql -c "DROP TABLE payments"')"
routing="$(payload 'Implement multi-tenant isolation strategy and define SLO/error budget')"
pii="$(payload 'echo phone=0912345678 > customer.txt')"
placeholder="$(payload 'echo phone=0901234xxx email=user@example.com > fixture.txt')"
write="$(payload 'echo updated >> skills/backend-pack/SKILL.md')"

case_out "tool safe allowed" 'permissionDecision":"allow' "printf '%s' '$safe' | TOOL_GUARD_MODE=block bash tool-guardian/guard-tool.sh"
case_out "tool rm blocked" 'permissionDecision":"deny' "printf '%s' '$rmrf' | TOOL_GUARD_MODE=block bash tool-guardian/guard-tool.sh"
case_out "tool force blocked" 'permissionDecision":"deny' "printf '%s' '$force' | TOOL_GUARD_MODE=block bash tool-guardian/guard-tool.sh"
case_out "tool drop blocked" 'permissionDecision":"deny' "printf '%s' '$drop' | TOOL_GUARD_MODE=block bash tool-guardian/guard-tool.sh"
case_out "routing coding block" 'permissionDecision":"deny' "printf '%s' '$routing' | ACTIVE_AGENT=coding ROUTING_GUARD_MODE=block bash routing-guard/check-boundary.sh"
case_out "routing ce7 allow" 'permissionDecision":"allow' "printf '%s' '$routing' | ACTIVE_AGENT=ce7 ROUTING_GUARD_MODE=block bash routing-guard/check-boundary.sh"
case_out "pii real blocked" 'permissionDecision":"deny' "printf '%s' '$pii' | PII_MODE=block bash pii-scanner/scan-pii.sh"
case_out "pii placeholder allowed" 'permissionDecision":"allow' "printf '%s' '$placeholder' | PII_MODE=block bash pii-scanner/scan-pii.sh"
case_out "update reminder" 'additionalContext' "printf '%s' '$write' | bash update-reminder/remind-update.sh"

printf 'github_pat_1234567890abcdefghijklmnopqrstuvwxyzABCDEF\n' > "$TMP/secret.txt"
case_status "secrets block" 1 'Secrets Scanner found' "SECRETS_SCAN_TARGETS='$TMP/secret.txt' SCAN_MODE=block bash secrets-scanner/scan-secrets.sh < /dev/null"

(
  cd "$TMP"
  mkdir -p .handoffs/ADR-2026-05-example
  printf 'ADR-2026-05-example\n' > .handoffs/.active
  cat > .handoffs/ADR-2026-05-example/input-package.yaml <<'YAML'
adr_id: ADR-2026-05-example
title: Example
risk_class: medium
contract:
  format: openapi
idempotency:
  key_shape: N/A
slo:
  latency_p99_ms: N/A
data_lifecycle:
  source_of_truth: test
security:
  authz: test
rollout:
  rollback: test
runbook_stub:
  metric_to_watch: test
on_call_owner: test
YAML
  "$ROOT/attestation/attest-handoff.sh" >/dev/null
  printf '{}' | bash "$ROOT/context-injection/inject-context.sh" | grep -q 'additionalContext'
  printf '{}' | ACTIVE_AGENT=coding COMPLETION_GUARD_MODE=warn bash "$ROOT/completion-guard/check-complete.sh" | grep -q 'additionalContext'
  cat > .handoffs/ADR-2026-05-example/return-package.yaml <<'YAML'
adr_id: ADR-2026-05-example
status: implemented
YAML
  printf '{}' | bash "$ROOT/handoff-validator/validate-handoff.sh" | grep -q 'additionalContext'
  printf '{}' | bash "$ROOT/session-catchup/catchup.sh" | grep -q 'additionalContext'
  printf '{}' | bash "$ROOT/token-tracker/track-tokens.sh"
  test -f "$TOKEN_USAGE_HISTORY"
  printf '{}' | bash "$ROOT/memory-save/save-interaction.sh"
  test -f logs/copilot/memory/interaction-log.jsonl
)
echo "PASS handoff lifecycle hooks"; pass=$((pass+1))

while IFS= read -r script; do
  if bash -n "$script"; then echo "PASS syntax $script"; pass=$((pass+1)); else echo "FAIL syntax $script"; fail=$((fail+1)); fi
done < <(find . -name '*.sh' -not -path './tests/*' | sort)
python3 -m json.tool hooks.json >/dev/null && echo "PASS hooks.json" && pass=$((pass+1)) || { echo "FAIL hooks.json"; fail=$((fail+1)); }

echo "Summary: $pass passed, $fail failed"
[[ $fail -eq 0 ]]

