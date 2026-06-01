#!/usr/bin/env python3
"""CLI for the Skill-Retrieval index: search, get section, list, and a token-saving eval.

Examples:
    python3 skills_cli.py search --query "idempotency conflict" --pack backend-pack --k 3
    python3 skills_cli.py section --ref backend-pack/java-spring-boot --heading "Idempotency"
    python3 skills_cli.py list --pack database-pack
    python3 skills_cli.py stats
    python3 skills_cli.py token-eval --queries eval-queries.txt

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import skills_core as sc

CHARS_PER_TOKEN = 4


def _tok(n_chars: int) -> int:
    return round(n_chars / CHARS_PER_TOKEN)


def token_eval(queries: list[str]) -> dict:
    index = sc.build_index()
    file_chars: dict[str, int] = {}
    for ch in index:
        file_chars.setdefault(ch["path"], 0)
        file_chars[ch["path"]] += len(ch["body"]) + len(ch["heading"]) + 1

    rows = []
    total_retrieval = 0
    total_fullfile = 0
    for q in queries:
        res = sc.search_refs(q, k=3, index=index)
        retrieval_chars = len(json.dumps(res, ensure_ascii=False))
        paths = {r["path"] for r in res["results"]}
        fullfile_chars = sum(file_chars.get(p, 0) for p in paths) or 1
        total_retrieval += retrieval_chars
        total_fullfile += fullfile_chars
        rows.append(
            {
                "query": q,
                "hits": len(res["results"]),
                "retrieval_tokens": _tok(retrieval_chars),
                "fullfile_tokens": _tok(fullfile_chars),
                "saving_pct": round(100 * (1 - retrieval_chars / fullfile_chars), 1) if fullfile_chars else 0,
            }
        )
    overall = round(100 * (1 - total_retrieval / total_fullfile), 1) if total_fullfile else 0
    return {
        "queries": len(queries),
        "avg_retrieval_tokens": _tok(total_retrieval / max(1, len(queries))),
        "avg_fullfile_tokens": _tok(total_fullfile / max(1, len(queries))),
        "overall_saving_pct": overall,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Skill-Retrieval CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("--query", required=True)
    s.add_argument("--pack", default=None)
    s.add_argument("--k", type=int, default=3)

    g = sub.add_parser("section")
    g.add_argument("--ref", required=True)
    g.add_argument("--heading", default=None)

    ls = sub.add_parser("list")
    ls.add_argument("--pack", default=None)

    sub.add_parser("stats")

    te = sub.add_parser("token-eval")
    te.add_argument("--queries", required=True, help="file with one query per line")

    args = ap.parse_args()

    if args.cmd == "search":
        print(json.dumps(sc.search_refs(args.query, args.pack, args.k), ensure_ascii=False, indent=2))
    elif args.cmd == "section":
        print(json.dumps(sc.get_ref_section(args.ref, args.heading), ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        print(json.dumps(sc.list_refs(args.pack), ensure_ascii=False, indent=2))
    elif args.cmd == "stats":
        print(json.dumps(sc.stats(), ensure_ascii=False))
    elif args.cmd == "token-eval":
        queries = [l.strip() for l in Path(args.queries).read_text(encoding="utf-8").splitlines() if l.strip()]
        report = token_eval(queries)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

