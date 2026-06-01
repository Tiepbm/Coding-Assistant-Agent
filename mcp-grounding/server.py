#!/usr/bin/env python3
"""Local MCP server exposing grounding/verification tools.

Transport: stdio (launched by the IDE via .vscode/mcp.json). 100% local.

Tools:
    run_validator(root?)            -> run the repo pack validator, bounded verdict
    check_contract(text, format?)   -> lint OpenAPI / GraphQL / proto / JSON-schema fragment
    handoff_diff(local?, other?)    -> compare HANDOFF-PROTOCOL.md with the sibling repo

Smoke test (no mcp package needed):
    python3 server.py --selftest
"""
from __future__ import annotations

import sys

import grounding_core as gc

OPENAPI_SAMPLE = """openapi: 3.0.3
paths:
  /payments/{id}:
    get:
      operationId: getPayment
      responses:
        '200': { description: ok }
"""


def _selftest() -> int:
    print("validator:", gc.run_validator(".").get("ok"))
    print("contract:", gc.check_contract(OPENAPI_SAMPLE))
    print("handoff:", gc.handoff_diff().get("ok"))
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        sys.stderr.write(
            "[agent-grounding] The 'mcp' package is not installed.\n"
            "Install it:  pip install -r mcp-grounding/requirements.txt\n"
            "The CLI (grounding_cli.py) still works without it.\n"
        )
        return 1

    server = FastMCP("agent-grounding")

    @server.tool()
    def run_validator(root: str | None = None) -> dict:
        """Run the repo's pack validator and return a bounded pass/fail verdict."""
        return gc.run_validator(root)

    @server.tool()
    def check_contract(text: str, format: str = "auto") -> dict:
        """Lint an OpenAPI / GraphQL SDL / proto / JSON-schema fragment before shipping it."""
        return gc.check_contract(text, format)

    @server.tool()
    def handoff_diff(local: str = "HANDOFF-PROTOCOL.md", other: str | None = None) -> dict:
        """Compare HANDOFF-PROTOCOL.md with the sibling repo (CE7 is canonical)."""
        return gc.handoff_diff(local, other)

    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

