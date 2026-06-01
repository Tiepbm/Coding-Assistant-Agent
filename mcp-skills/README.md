# Skill-Retrieval (MCP) — token-cheap reference layer

Indexes `skills/**/references/*.md` by heading so the agent pulls **only the matched section**
instead of loading a whole 250-line reference file. This is the biggest token saver in the
dual-agent system, and it also improves accuracy (the model sees the exact section, not a wall
of text).

## How it runs

- **100% local.** `server.py` is a Python process started by your IDE over stdio (`.vscode/mcp.json`).
- **Index source:** `skills/**/references/*.md` (override with `$SKILLS_DIR`). Built in-memory on
  each call, so it never drifts from the files. ~50 files is sub-second.

## Tools (MCP)

| Tool | When | Output |
|---|---|---|
| `search_refs(query, pack?, k)` | need deep content | top-k matched **sections**, ≤~600 tokens |
| `get_ref_section(ref_id, heading?)` | know the ref, want one section | the exact section(s) |
| `list_refs(pack?)` | choose what to retrieve | ref ids + their headings |

`ref_id` shape: `<pack>/<filename-without-.md>`, e.g. `backend-pack/java-spring-boot`.

## Routing model (keep native packs cheap)

Lop 1 — native pack routing (deterministic, cheap) stays as-is.
Lop 2 — when deep content is needed, call `search_refs` instead of loading the file.

## Setup

```bash
pip install -r mcp-skills/requirements.txt   # only for the live server
python3 mcp-skills/server.py --selftest       # smoke test (no mcp needed)
cd mcp-skills && python3 test_skills.py        # unit tests
```

Your IDE picks up `.vscode/mcp.json` automatically and starts the server.

## CLI + token saving proof

```bash
python3 mcp-skills/skills_cli.py search --query "idempotency conflict" --pack backend-pack --k 3
python3 mcp-skills/skills_cli.py section --ref backend-pack/java-spring-boot --heading "Idempotency"
python3 mcp-skills/skills_cli.py list --pack database-pack
python3 mcp-skills/skills_cli.py stats

# Measure tokens saved vs loading whole files:
python3 mcp-skills/skills_cli.py token-eval --queries mcp-skills/eval-queries.txt
```

`token-eval` reports `retrieval_tokens` vs `fullfile_tokens` per query and an overall saving %.

## Degradation

If the `mcp` package is not installed or MCP is disabled, the agent falls back to normal
progressive disclosure (load the single most relevant reference file). Nothing breaks.

