#!/usr/bin/env python3
"""Local MCP server exposing the dual-agent learning memory.

Transport: stdio (launched by the IDE via .vscode/mcp.json). 100% local, no cloud.
Storage: SQLite at $MEMORY_DB (default ~/.copilot-agent-memory/<agent>.db).

Tools:
    recall(query, k)            -> bounded patterns + corrections (≤~200 tokens)
    record_outcome(...)         -> persist an interaction outcome
    record_correction(...)      -> persist a routing miss
    synthesize()                -> recompute pattern confidence
    get_stats()                 -> totals + routing-accuracy proxy
    export_patterns(path)       -> write a human-readable learned-patterns file

Run manually for a smoke test:
    python3 server.py --selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

import memory_core as mc


def _selftest() -> int:
    conn = mc.connect()
    mc.record_outcome(
        conn, prompt_summary="selftest payment idempotency",
        packs="backend-pack,database-pack", domain="banking", risk_class="medium",
        outcome="accepted", source="manual",
    )
    print("recall:", mc.recall(conn, "payment idempotency"))
    print("stats:", mc.get_stats(conn))
    conn.close()
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        sys.stderr.write(
            "[agent-memory] The 'mcp' package is not installed.\n"
            "Install it:  pip install -r mcp-memory/requirements.txt\n"
            "The hook-based CLI (memory_cli.py) still works without it.\n"
        )
        return 1

    server = FastMCP("agent-memory")

    @server.tool()
    def recall(query: str, k: int = 3) -> dict:
        """Recall relevant past routing patterns + corrections for a prompt.

        Call before routing on medium+/multi-pack tasks. Output is bounded (~200 tokens)."""
        conn = mc.connect()
        try:
            return mc.recall(conn, query, k)
        finally:
            conn.close()

    @server.tool()
    def record_outcome(
        prompt_summary: str,
        packs: list[str],
        refs: list[str] | None = None,
        domain: str | None = None,
        risk_class: str | None = None,
        outcome: str = "accepted",
    ) -> dict:
        """Persist an interaction outcome. Summary + metadata only — no prompt/code/PII."""
        conn = mc.connect()
        try:
            rid = mc.record_outcome(
                conn, prompt_summary=prompt_summary, packs=packs, refs=refs or [],
                domain=domain, risk_class=risk_class, outcome=outcome, source="mcp",
            )
            return {"id": rid}
        finally:
            conn.close()

    @server.tool()
    def record_correction(
        prompt_summary: str, expected_packs: list[str], actual_packs: list[str], root_cause: str
    ) -> dict:
        """Persist a routing miss so the wrong pattern's confidence drops."""
        conn = mc.connect()
        try:
            rid = mc.record_correction(
                conn, prompt_summary=prompt_summary, expected_packs=expected_packs,
                actual_packs=actual_packs, root_cause=root_cause,
            )
            return {"id": rid}
        finally:
            conn.close()

    @server.tool()
    def synthesize() -> dict:
        """Recompute pattern confidence from stored interactions."""
        conn = mc.connect()
        try:
            return mc.synthesize(conn)
        finally:
            conn.close()

    @server.tool()
    def get_stats() -> dict:
        """Return totals + routing-accuracy proxy + top patterns."""
        conn = mc.connect()
        try:
            return mc.get_stats(conn)
        finally:
            conn.close()

    @server.tool()
    def export_patterns(path: str) -> dict:
        """Export high-confidence patterns to a human-readable markdown file."""
        conn = mc.connect()
        try:
            n = mc.export_patterns(conn, Path(path))
            return {"exported": n, "path": path}
        finally:
            conn.close()

    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

