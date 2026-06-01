#!/usr/bin/env python3
"""CLI for the grounding tools (also handy for CI / hooks).

Examples:
    python3 grounding_cli.py validate
    python3 grounding_cli.py contract --file spec.yaml
    python3 grounding_cli.py contract --format proto --file svc.proto
    python3 grounding_cli.py handoff --other ../software-engineering-agent/HANDOFF-PROTOCOL.md

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import grounding_core as gc


def main() -> int:
    ap = argparse.ArgumentParser(description="Grounding/verification CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--root", default=None)

    c = sub.add_parser("contract")
    c.add_argument("--file", default=None)
    c.add_argument("--text", default=None)
    c.add_argument("--format", default="auto")

    h = sub.add_parser("handoff")
    h.add_argument("--local", default="HANDOFF-PROTOCOL.md")
    h.add_argument("--other", default=None)

    args = ap.parse_args()

    if args.cmd == "validate":
        res = gc.run_validator(args.root)
    elif args.cmd == "contract":
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        elif args.text:
            text = args.text
        else:
            text = sys.stdin.read()
        res = gc.check_contract(text, args.format)
    elif args.cmd == "handoff":
        res = gc.handoff_diff(args.local, args.other)
    else:  # pragma: no cover
        return 2

    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

