#!/usr/bin/env python3
"""Check token budgets against eval responses.

Usage:
    python3 scripts/check_token_budgets.py \
        --responses runs/20260505/responses.jsonl \
        --budgets evals/token-budget.jsonl

Output: per-task token verdict (PASS/WARN/FAIL) + summary.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    results = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            results.append(json.loads(line))
    return results


def get_budget_for_task(n_packs: int, budgets: dict[str, dict]) -> dict:
    """Select appropriate budget based on number of packs activated."""
    if n_packs == 0:
        return budgets.get("budget-agent", {"max_input_tokens": 5000, "max_output_tokens": 2000})
    elif n_packs == 1:
        return budgets.get("budget-single-pack", {"max_input_tokens": 12000, "max_output_tokens": 3000})
    else:
        return budgets.get("budget-multi-pack", {"max_input_tokens": 20000, "max_output_tokens": 5000})


def main() -> int:
    parser = argparse.ArgumentParser(description="Check token budgets")
    parser.add_argument("--responses", required=True, help="Path to responses JSONL (with tokens field)")
    parser.add_argument("--budgets", required=True, help="Path to token-budget JSONL")
    parser.add_argument("--fail-threshold", type=float, default=1.5, help="Ratio above budget to FAIL (default 1.5x)")
    parser.add_argument("--warn-threshold", type=float, default=1.2, help="Ratio above budget to WARN (default 1.2x)")
    args = parser.parse_args()

    responses_path = Path(args.responses)
    budgets_path = Path(args.budgets)

    if not responses_path.exists():
        print(f"ERROR: responses not found: {responses_path}")
        return 1
    if not budgets_path.exists():
        print(f"ERROR: budgets not found: {budgets_path}")
        return 1

    # Load
    responses = load_jsonl(responses_path)
    budget_list = load_jsonl(budgets_path)
    budgets = {b["id"]: b for b in budget_list}

    # Check each response
    results = []
    total_input = 0
    total_output = 0
    violations = []

    print(f"{'ID':<15} {'Input':>7} {'Output':>7} {'Budget':>7} {'Ratio':>6} {'Verdict'}")
    print("-" * 65)

    for resp in responses:
        tokens = resp.get("tokens")
        if not tokens:
            print(f"{resp['id']:<15} {'N/A':>7} {'N/A':>7} {'N/A':>7} {'N/A':>6} SKIP (no token data)")
            continue

        n_packs = len(resp.get("packs_invoked", []))
        budget = get_budget_for_task(n_packs, budgets)
        max_input = budget.get("max_input_tokens", 12000)

        actual_input = tokens.get("input", 0)
        actual_output = tokens.get("output", 0)
        total_input += actual_input
        total_output += actual_output

        ratio = actual_input / max_input if max_input > 0 else 0

        if ratio > args.fail_threshold:
            verdict = "FAIL"
            violations.append(f"{resp['id']} exceeded budget by {ratio:.1f}x ({actual_input} vs {max_input})")
        elif ratio > args.warn_threshold:
            verdict = "WARN"
        else:
            verdict = "PASS"

        print(f"{resp['id']:<15} {actual_input:>7} {actual_output:>7} {max_input:>7} {ratio:>5.2f}x {verdict}")

        results.append({
            "id": resp["id"],
            "input_tokens": actual_input,
            "output_tokens": actual_output,
            "budget": max_input,
            "ratio": round(ratio, 2),
            "verdict": verdict,
        })

    # Summary
    n_tasks = len(results)
    n_pass = sum(1 for r in results if r["verdict"] == "PASS")
    n_warn = sum(1 for r in results if r["verdict"] == "WARN")
    n_fail = sum(1 for r in results if r["verdict"] == "FAIL")

    print(f"\n{'='*65}")
    print(f"Summary: {n_tasks} tasks | {n_pass} PASS | {n_warn} WARN | {n_fail} FAIL")
    print(f"Total tokens: {total_input + total_output:,} (input: {total_input:,}, output: {total_output:,})")
    if n_tasks > 0:
        print(f"Avg per task: {(total_input + total_output) // n_tasks:,} tokens")

    # Estimate cost (Claude Sonnet pricing)
    cost = (total_input * 3 + total_output * 15) / 1_000_000
    print(f"Estimated cost: ${cost:.4f} (Sonnet pricing: $3/M in, $15/M out)")

    if violations:
        print(f"\nBudget violations ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")

    return 1 if n_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
