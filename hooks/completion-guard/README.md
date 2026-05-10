# Completion Guard

`agentStop` hook that checks active handoff completeness.

## CE7 mode

Requires `.handoffs/<ADR>/input-package.yaml` with required implementation package fields.

## Coding mode

Requires `.handoffs/<ADR>/return-package.yaml` with `status: implemented | partial | blocked`. For `implemented`, it requires Self-Review sections.

## Environment

- `COMPLETION_GUARD_MODE=warn|block` default `warn`.
- `ACTIVE_AGENT=ce7|coding|auto`.
- `SKIP_COMPLETION_GUARD=true`.

