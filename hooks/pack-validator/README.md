# Pack Validator

Warn-only `sessionEnd` hook that runs the local agent package validator when package files changed.

## Behavior

- Checks git diff for changes under `skills/`, `agents/`, `instructions/`, `evals/`, or `.github/skills|agents|instructions`.
- Runs `python3 scripts/validate_packs.py` for Coding Assistant repos.
- Runs `python3 scripts/validate_hybrid_packs.py` for CE7 repos.
- Logs pass/fail to `logs/copilot/pack-validator/validator.log`.
- Never blocks `sessionEnd`.

## Environment

- `SKIP_PACK_VALIDATOR=true`
- `PACK_VALIDATOR_LOG_DIR=logs/copilot/pack-validator`

