# Session Logger

Writes local JSONL audit logs for Copilot sessions.

## Files

- `logs/copilot/sessions/session.log` — session start/end.
- `logs/copilot/sessions/prompts.log` — prompt length metadata only.
- `logs/copilot/sessions/errors.log` — error event metadata.

Prompt bodies are not stored by default; only length is logged to reduce PII exposure.

## Environment

- `SKIP_LOGGING=true`
- `SESSION_LOG_DIR=logs/copilot/sessions`
- `ACTIVE_AGENT=auto|coding|ce7`

