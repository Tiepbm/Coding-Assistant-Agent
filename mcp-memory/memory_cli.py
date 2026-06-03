#!/usr/bin/env python3
"""CLI wrapper around memory_core, used by hooks for fully-automatic capture.

Examples:
    python3 memory_cli.py record-outcome --summary "payment idempotency" \
        --packs backend-pack,database-pack --domain banking --risk medium --outcome auto
    python3 memory_cli.py recall --query "payment idempotency" --k 3
    python3 memory_cli.py synthesize
    python3 memory_cli.py stats
    python3 memory_cli.py export --out memory/learned-patterns.auto.md
    python3 memory_cli.py report --out reports/accuracy-history.jsonl

No third-party dependencies. Safe to call from a hook; never raises to the caller
(exit 0 on soft errors) so it cannot break an agent session.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import memory_core as mc


def main() -> int:
    ap = argparse.ArgumentParser(description="Dual-agent memory CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ro = sub.add_parser("record-outcome")
    ro.add_argument("--summary", required=True)
    ro.add_argument("--packs", default="")
    ro.add_argument("--refs", default="")
    ro.add_argument("--domain", default=None)
    ro.add_argument("--risk", default=None)
    ro.add_argument("--outcome", default="auto")
    ro.add_argument("--source", default="hook")

    rc = sub.add_parser("record-correction")
    rc.add_argument("--summary", required=True)
    rc.add_argument("--expected", required=True)
    rc.add_argument("--actual", required=True)
    rc.add_argument("--root-cause", required=True)

    rq = sub.add_parser("recall")
    rq.add_argument("--query", required=True)
    rq.add_argument("--k", type=int, default=3)

    si = sub.add_parser("search-index")
    si.add_argument("--query", required=True)
    si.add_argument("--k", type=int, default=8)

    gd = sub.add_parser("get-details")
    gd.add_argument("--ids", required=True, help="Comma-separated IDs, e.g. 12,13,29")

    sub.add_parser("synthesize")
    sub.add_parser("stats")

    ex = sub.add_parser("export")
    ex.add_argument("--out", required=True)

    rp = sub.add_parser("report")
    rp.add_argument("--out", required=True)

    pr = sub.add_parser("promote")
    pr.add_argument("--out", default="memory/learned-patterns.md")
    pr.add_argument("--min-freq", type=int, default=3)
    pr.add_argument("--min-conf", type=float, default=0.7)
    pr.add_argument("--min-corr", type=int, default=2)
    pr.add_argument("--synthesize", action="store_true", help="recompute confidence before promoting")

    args = ap.parse_args()

    try:
        conn = mc.connect()
    except Exception as e:  # never break the caller
        print(json.dumps({"ok": False, "error": str(e)}))
        return 0

    try:
        if args.cmd == "record-outcome":
            rid = mc.record_outcome(
                conn,
                prompt_summary=args.summary,
                packs=args.packs,
                refs=args.refs,
                domain=args.domain,
                risk_class=args.risk,
                outcome=args.outcome,
                source=args.source,
            )
            print(json.dumps({"ok": True, "id": rid}))
        elif args.cmd == "record-correction":
            rid = mc.record_correction(
                conn,
                prompt_summary=args.summary,
                expected_packs=args.expected,
                actual_packs=args.actual,
                root_cause=args.root_cause,
            )
            print(json.dumps({"ok": True, "id": rid}))
        elif args.cmd == "recall":
            print(json.dumps({"ok": True, **mc.recall(conn, args.query, args.k)}, ensure_ascii=False))
        elif args.cmd == "search-index":
            print(json.dumps({"ok": True, **mc.search_memory_index(conn, args.query, args.k)}, ensure_ascii=False))
        elif args.cmd == "get-details":
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            print(json.dumps({"ok": True, **mc.get_memory_details(conn, ids)}, ensure_ascii=False))
        elif args.cmd == "synthesize":
            print(json.dumps({"ok": True, **mc.synthesize(conn)}))
        elif args.cmd == "stats":
            print(json.dumps({"ok": True, **mc.get_stats(conn)}, ensure_ascii=False))
        elif args.cmd == "export":
            n = mc.export_patterns(conn, Path(args.out))
            print(json.dumps({"ok": True, "exported": n, "path": args.out}))
        elif args.cmd == "report":
            entry = mc.report_accuracy(conn, Path(args.out))
            print(json.dumps({"ok": True, **entry}, ensure_ascii=False))
        elif args.cmd == "promote":
            if args.synthesize:
                mc.synthesize(conn)
            res = mc.promote_to_file(
                conn, Path(args.out),
                min_freq=args.min_freq, min_conf=args.min_conf, min_corr=args.min_corr,
            )
            print(json.dumps({"ok": True, **res, "path": args.out}, ensure_ascii=False))
    except Exception as e:  # soft-fail
        print(json.dumps({"ok": False, "error": str(e)}))
        return 0
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

