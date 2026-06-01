#!/usr/bin/env python3
"""Local MCP server exposing the dual-agent reference layer for token-cheap retrieval.

Transport: stdio (launched by the IDE via .vscode/mcp.json). 100% local.
Index source: `skills/**/references/*.md` ($SKILLS_DIR override supported).

Tools:
    search_refs(query, pack?, k)   -> top-k matched heading sections (≤~600 tokens)
    get_ref_section(ref_id, head?) -> the exact section(s) of one reference
    list_refs(pack?)               -> reference ids + their headings (routing aid)

Smoke test (no mcp package needed):
    python3 server.py --selftest
"""
from __future__ import annotations

import sys

import skills_core as sc


def _selftest() -> int:
    print("stats:", sc.stats())
    res = sc.search_refs("idempotency", k=2)
    print("search hits:", [(r["ref_id"], r["heading"]) for r in res["results"]])
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        sys.stderr.write(
            "[agent-skills] The 'mcp' package is not installed.\n"
            "Install it:  pip install -r mcp-skills/requirements.txt\n"
            "The CLI (skills_cli.py) still works without it.\n"
        )
        return 1

    server = FastMCP("agent-skills")

    @server.tool()
    def search_refs(query: str, pack: str | None = None, k: int = 3) -> dict:
        """Return the top-k matched reference SECTIONS for a query (token-cheap).

        Prefer this over loading a whole reference file. Output is bounded (~600 tokens)."""
        return sc.search_refs(query, pack, k)

    @server.tool()
    def get_ref_section(ref_id: str, heading: str | None = None) -> dict:
        """Return the exact section(s) of one reference (e.g. ref_id='backend-pack/java-spring-boot')."""
        return sc.get_ref_section(ref_id, heading)

    @server.tool()
    def list_refs(pack: str | None = None) -> dict:
        """List reference ids and their headings for a pack (helps choose what to retrieve)."""
        return sc.list_refs(pack)

    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

