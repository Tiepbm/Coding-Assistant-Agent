# Agent Memory (MCP) — local, automatic learning loop

Local SQLite-backed memory that makes the agent **more accurate after each answer**, with
**zero manual work** and **zero cloud cost**.

## How it runs

- **100% local.** `server.py` is a Python process started by your IDE over stdio (see
  `.vscode/mcp.json`). Nothing leaves your machine.
- **Storage:** SQLite at `$MEMORY_DB` (default `~/.copilot-agent-memory/<agent>.db`).
- **Privacy:** stores **summaries + metadata only** — never prompt bodies, code, secrets, or PII.

## Two write paths (both automatic)

| Path | Trigger | Who calls it | Needs `mcp` pkg? |
|---|---|---|---|
| MCP tool | The agent calls `record_outcome` / `record_correction` while answering | the model | yes |
| Hook CLI | `sessionEnd` hook runs `memory_cli.py record-outcome ...` | the hook (no model) | **no** |

The hook path guarantees capture **even if the model forgets** to call the tool. Both paths
write to the same DB through `memory_core.py`.

## Tools (MCP)

| Tool | When | Output |
|---|---|---|
| `recall(query, k)` | before routing (risk ≥ medium / multi-pack) | ≤~200-token patterns + corrections |
| `record_outcome(...)` | after answering | `{id}` |
| `record_correction(...)` | on a routing miss | `{id}` |
| `synthesize()` | periodic / every ~20 interactions | `{patterns}` |
| `get_stats()` | on demand | totals + routing-accuracy proxy |
| `export_patterns(path)` | degradation / review | writes markdown |

## Automatic scoring / evaluation

- Each interaction stores an `outcome` → score (`accepted=1.0, edited=0.6, repeated=0.3, rejected=0.0`).
- `synthesize()` folds outcomes into per-pattern `confidence`.
- `recall()` returns high-confidence patterns first, so routing improves over time.
- `report` appends a weekly snapshot to `reports/accuracy-history.jsonl` (run by hook/workflow):

```bash
python3 mcp-memory/memory_cli.py report --out reports/accuracy-history.jsonl
```

## Setup

```bash
# 1. (optional) install the MCP SDK to enable the live server
pip install -r mcp-memory/requirements.txt

# 2. smoke-test the core without the SDK
python3 mcp-memory/server.py --selftest

# 3. run the unit tests
cd mcp-memory && python3 test_memory.py
```

Your IDE picks up `.vscode/mcp.json` automatically and starts the server.

## CLI (used by hooks, also handy manually)

```bash
python3 mcp-memory/memory_cli.py record-outcome \
  --summary "payment idempotency" --packs backend-pack,database-pack \
  --domain banking --risk medium --outcome accepted

python3 mcp-memory/memory_cli.py recall --query "payment idempotency" --k 3
python3 mcp-memory/memory_cli.py synthesize
python3 mcp-memory/memory_cli.py stats
python3 mcp-memory/memory_cli.py export --out memory/learned-patterns.auto.md
```

## Degradation

If the `mcp` package is not installed or the IDE has MCP disabled, the agent falls back to
reading `memory/learned-patterns.md`. The hook CLI keeps capturing data regardless, so the
DB stays warm for when MCP is enabled.

