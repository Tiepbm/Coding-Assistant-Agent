# Tool Guardian

Blocks high-risk operations before Copilot executes a tool call.

## Blocks by default

- `rm -rf /`, `rm -rf .`, deleting `.env` or `.git`
- `git push --force` / `-f` to `main` or `master`
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, unscoped `DELETE FROM table;`
- `chmod 777`
- `curl | bash`, `wget | sh`, `curl --data @file`
- `sudo`, `npm publish`

## Contract

Reads Copilot event JSON on stdin. Parses both modern `toolArgs` JSON-string payloads and legacy `toolInput` payloads.

Deny output:

```json
{"permissionDecision":"deny","permissionDecisionReason":"Tool Guardian blocked ..."}
```

## Environment

- `TOOL_GUARD_MODE=block|warn` (default `block`)
- `SKIP_TOOL_GUARD=true`
- `TOOL_GUARD_ALLOWLIST="pattern1,pattern2"`
- `TOOL_GUARD_LOG_DIR=logs/copilot/tool-guardian`

