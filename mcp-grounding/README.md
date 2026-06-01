# Grounding (MCP) — self-verify before finalizing

Local tools that let the agent **check its own work** before shipping an answer, instead of
"confidently guessing" on contracts, validators, or the handoff protocol.

## How it runs

- **100% local.** `server.py` is a Python process started by your IDE over stdio (`.vscode/mcp.json`).
- No third-party deps for the core/CLI. PyYAML (optional) improves OpenAPI YAML linting.

## Tools (MCP)

| Tool | Use when | Output |
|---|---|---|
| `run_validator(root?)` | after editing packs/skills | `{ok, exit_code, tail}` (bounded) |
| `check_contract(text, format?)` | before shipping an OpenAPI/GraphQL/proto/JSON-schema fragment | `{ok, format, errors, warnings}` |
| `handoff_diff(local?, other?)` | before/after touching `HANDOFF-PROTOCOL.md` | `{ok, identical, diff, fix}` |

`check_contract` auto-detects the format; linting is **heuristic** (catches common structural
mistakes — missing version, empty paths, unbalanced braces, missing rpc — not full validation).

## Setup

```bash
pip install -r mcp-grounding/requirements.txt   # only for the live server
python3 mcp-grounding/server.py --selftest        # smoke test (no mcp needed)
cd mcp-grounding && python3 test_grounding.py      # unit tests
```

## CLI

```bash
python3 mcp-grounding/grounding_cli.py validate
python3 mcp-grounding/grounding_cli.py contract --file spec.yaml
python3 mcp-grounding/grounding_cli.py contract --format proto --file svc.proto
python3 mcp-grounding/grounding_cli.py handoff --other ../software-engineering-agent/HANDOFF-PROTOCOL.md
```

Exit code is `0` on pass, `1` on fail — usable directly in CI or a pre-commit hook.

## Degradation

If the `mcp` package is not installed, the agent simply skips tool-based grounding and relies
on its built-in guardrails. Nothing breaks.

