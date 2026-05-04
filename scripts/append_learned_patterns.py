#!/usr/bin/env python3
"""Append learned patterns from eval run results to memory/learned-patterns.md.

Usage:
    python3 scripts/append_learned_patterns.py --report runs/20260505/report.json

Reads the eval report, identifies:
- Tasks that failed (score < 75) — logs the failure pattern
- Routing corrections (wrong pack activated) — logs the correction
- New anti-patterns discovered — logs the anti-pattern

Appends entries to memory/learned-patterns.md in the standard format.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_FILE = ROOT / "memory" / "learned-patterns.md"
ROUTING_CORRECTIONS_FILE = ROOT / "memory" / "routing-corrections.jsonl"


def load_report(report_path: Path) -> dict:
    return json.loads(report_path.read_text(encoding="utf-8"))


def extract_patterns(report: dict) -> list[dict]:
    """Extract actionable patterns from eval report."""
    patterns = []
    today = date.today().isoformat()

    results = report.get("results", [])
    for result in results:
        task_id = result.get("id", "unknown")
        score = result.get("score", 100)
        routing_correct = result.get("routing_correct", True)
        expected_pack = result.get("expected_pack", "")
        actual_pack = result.get("actual_pack", "")

        # Failed task — learn from it
        if score < 75:
            patterns.append({
                "date": today,
                "type": "failure",
                "task_id": task_id,
                "score": score,
                "summary": f"Task {task_id} scored {score}/100",
                "expected_pack": expected_pack,
            })

        # Routing correction
        if not routing_correct and expected_pack and actual_pack:
            patterns.append({
                "date": today,
                "type": "routing_correction",
                "task_id": task_id,
                "expected": expected_pack,
                "actual": actual_pack,
                "summary": f"Routed to {actual_pack} instead of {expected_pack}",
            })

    return patterns


def append_to_memory(patterns: list[dict]) -> int:
    """Append patterns to learned-patterns.md. Returns count appended."""
    if not patterns:
        return 0

    existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
    new_entries = []

    for p in patterns:
        # Skip if already logged (dedup by task_id + date)
        dedup_key = f"{p['date']}: {p['task_id']}"
        if dedup_key in existing:
            continue

        if p["type"] == "failure":
            entry = f"""
## {p['date']}: Eval failure — {p['task_id']}

- Symptom: scored {p['score']}/100 (below 75 threshold).
- Root cause: TBD (manual review needed).
- Fix: TBD.
- Benchmark case: `{p['task_id']}`.
- Owner: maintainers.
"""
        elif p["type"] == "routing_correction":
            entry = f"""
## {p['date']}: Routing correction — {p['task_id']}

- Symptom: routed to `{p['actual']}` instead of `{p['expected']}`.
- Root cause: ambiguous trigger or missing disambiguation.
- Fix: update Pack Disambiguation table or Tie-Break Rules.
- Benchmark case: `{p['task_id']}`.
- Owner: maintainers.
"""
        else:
            continue

        new_entries.append(entry)

    if new_entries:
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(entry)

    return len(new_entries)


def append_routing_corrections(patterns: list[dict]) -> int:
    """Append routing corrections to routing-corrections.jsonl."""
    corrections = [p for p in patterns if p["type"] == "routing_correction"]
    if not corrections:
        return 0

    with open(ROUTING_CORRECTIONS_FILE, "a", encoding="utf-8") as f:
        for c in corrections:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    return len(corrections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Append learned patterns from eval report")
    parser.add_argument("--report", required=True, help="Path to eval report JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print patterns without appending")
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: report not found: {report_path}")
        return 1

    report = load_report(report_path)
    patterns = extract_patterns(report)

    if args.dry_run:
        print(f"Found {len(patterns)} patterns:")
        for p in patterns:
            print(f"  [{p['type']}] {p['summary']}")
        return 0

    n_memory = append_to_memory(patterns)
    n_routing = append_routing_corrections(patterns)

    print(f"Appended {n_memory} entries to memory/learned-patterns.md")
    print(f"Appended {n_routing} entries to memory/routing-corrections.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
