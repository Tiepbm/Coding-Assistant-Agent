# Dual-Agent Copilot Hooks

Shared GitHub Copilot hooks for the CE7 + Coding Assistant dual-agent system.

## Hooks

| Hook | Event | Default | Purpose |
|---|---|---|---|
| `tool-guardian` | `preToolUse` | block | Deny destructive shell/git/database operations. |
| `routing-guard` | `preToolUse` | warn | Warn when Coding Assistant crosses into CE7-owned decisions. |
| `pii-scanner` | `preToolUse` | block | Block likely real PII in tool inputs before writes. |
| `context-injection` | `preToolUse` | allow | Inject active `.handoffs/<ADR>` context with SHA-256 attestation protection. |
| `update-reminder` | `postToolUse` | remind | Remind agents to update handoff progress/Self-Review after edits. |
| `handoff-validator` | `postToolUse` | warn | Validate handoff input/return package shape. |
| `completion-guard` | `agentStop` | warn | Check active handoff package completeness before stopping. |
| `session-logger` | session lifecycle | log | Write local JSONL audit logs. |
| `session-catchup` | `sessionStart` | context | Recover active ADR/progress/diff state. |
| `secrets-scanner` | `sessionEnd` | warn | Scan changed files for likely credentials. |
| `token-tracker` | `sessionEnd` | log | Record token/cost proxy metrics. |
| `memory-save` | `sessionEnd` | log | Append privacy-safe interaction metadata. |
| `pack-validator` | `sessionEnd` | warn | Run the repo validator when agent-package files changed. |
| `attestation` | manual | n/a | Attest `input-package.yaml` or `HANDOFF-PROTOCOL.md`. |

## Copilot contract

Pre-tool scripts parse Copilot `toolArgs` as a JSON string and return structured decisions:

```json
{"permissionDecision":"deny","permissionDecisionReason":"..."}
```

Warn-only pre-tool hooks return:

```json
{"permissionDecision":"allow"}
```

## Install into a project

```bash
mkdir -p your-project/.github/hooks
cp -R hooks/. your-project/.github/hooks/
find your-project/.github/hooks -name "*.sh" -exec chmod +x {} +
printf '\nlogs/copilot/\n' >> your-project/.gitignore
```

## Test

```bash
bash hooks/tests/run-hooks-tests.sh
```

Current suite covers guardrails, PII, secrets, context injection, attestation, completion, handoff validation, memory/token logging, shell syntax, and `hooks.json` syntax.

## Tuning

| Variable | Default | Description |
|---|---|---|
| `TOOL_GUARD_MODE` | `block` | `block` denies threats; `warn` logs only. |
| `ROUTING_GUARD_MODE` | `warn` | Start in `warn`; switch to `block` after false-positive tuning. |
| `ACTIVE_AGENT` | `auto` | `coding`, `ce7`, or `auto` based on repo/payload. |
| `SKIP_TOOL_GUARD` | unset | Set `true` for reviewed exceptions. |
| `SKIP_ROUTING_GUARD` | unset | Set `true` for reviewed exceptions. |
| `PII_MODE` | `block` | `block` denies likely real PII; `warn` logs only. |
| `SCAN_MODE` | `warn` | `secrets-scanner` mode. |
| `COMPLETION_GUARD_MODE` | `warn` | Set `block` after tuning handoff workflow. |

