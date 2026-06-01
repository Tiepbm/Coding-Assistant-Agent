# MCP Usage — Coding Assistant Agent

Local, automatic learning + token-saving via 3 MCP servers. 100% local, no cloud.
For the cross-repo overview see the workspace `USAGE-mcp-dual-agent.md`.

## Servers in this repo

| Server | Config env | Purpose |
|---|---|---|
| `agent-memory` | `MEMORY_AGENT=coding` | recall / record_outcome / promote (learning loop) |
| `agent-skills` | `SKILLS_DIR=skills` | `search_refs` → matched section only (**−82.9% tokens**) |
| `agent-grounding` | `GROUNDING_ROOT=.` | `run_validator` / `check_contract` / `handoff_diff` |

Memory DB: `~/.copilot-agent-memory/coding.db` (local, outside the repo).

## JetBrains (WebStorm / Rider / IntelliJ): per-project, not global

The server process always runs locally. Put the **config per-project** (this repo), because
the memory DB and paths are repo-specific — a global config would collide with CE7's.

- **Junie:** auto-reads `.junie/mcp/mcp.json` (already in this repo). Nothing to do.
- **AI Assistant:** `Settings | Tools | AI Assistant | Model Context Protocol` → `Add` → `As JSON`
  → paste `.junie/mcp/mcp.json`, scope **Project**.

## VS Code

Auto-reads `.vscode/mcp.json` (already in this repo).

## One-time install

```bash
pip install -r mcp-memory/requirements.txt   # 'mcp' powers all 3 servers
python3 mcp-memory/server.py --selftest
python3 mcp-skills/server.py --selftest
python3 mcp-grounding/server.py --selftest
```

Without `mcp`, auto-capture still runs via the `sessionEnd` hook and all CLIs still work; the
agent degrades gracefully (reads `memory/learned-patterns.md`, loads one reference).

## What is automatic

- Every session: the `memory-save` hook records a privacy-safe interaction into the DB.
- Weekly / on-demand: `weekly-pattern-synthesis` workflow or `.github/prompts/memory-synthesis.prompt.md` runs
  `synthesize` → `report` → `promote`, appending a `## PROPOSED` block to `memory/learned-patterns.md` for PR review.

## Measure

```bash
python3 mcp-skills/skills_cli.py token-eval --queries mcp-skills/eval-queries.txt
python3 mcp-memory/memory_cli.py stats
```

More detail: `mcp-memory/README.md`, `mcp-skills/README.md`, `mcp-grounding/README.md`.

