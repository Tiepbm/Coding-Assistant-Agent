# Context Injection

`preToolUse` hook that injects active `.handoffs/<ADR>/` context into the agent loop.

If `.handoffs/<ADR>/.attestation` exists, `input-package.yaml` is injected only when the current SHA-256 matches the attested hash. On mismatch, the hook emits a tamper warning instead of file content.

## Environment

- `SKIP_CONTEXT_INJECTION=true`
- `HANDOFF_CONTEXT_LINES=60`
- `ACTIVE_AGENT=ce7|coding|auto`

