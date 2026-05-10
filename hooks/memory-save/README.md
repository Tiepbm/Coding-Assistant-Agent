# Memory Save

`sessionEnd` hook that appends privacy-safe session metadata to `memory/interaction-log.jsonl` when available, otherwise to `logs/copilot/memory/interaction-log.jsonl`.

It stores file paths, likely packs, active ADR, and handoff status. It does not store prompt bodies or file contents.

## Environment

- `SKIP_MEMORY_SAVE=true`
- `MEMORY_LOG_FILE=memory/interaction-log.jsonl`

