# Update Reminder

`postToolUse` hook that nudges the active agent to update `.handoffs/<ADR>/progress.md` and `return-package.yaml` after writes/edits.

Also reminds maintainers to run validators when package files under `skills/`, `agents/`, `instructions/`, or `evals/` change.

## Environment

- `SKIP_UPDATE_REMINDER=true`

