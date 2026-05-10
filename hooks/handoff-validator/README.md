# Handoff Validator

`postToolUse` hook that validates `.handoffs/<ADR>/input-package.yaml` and `return-package.yaml` against the required shape from `HANDOFF-PROTOCOL.md`.

It is warn-only and emits `additionalContext` when fields are missing.

## Environment

- `SKIP_HANDOFF_VALIDATOR=true`
- `HANDOFF_VALIDATOR_LOG_DIR=logs/copilot/handoff-validator`

