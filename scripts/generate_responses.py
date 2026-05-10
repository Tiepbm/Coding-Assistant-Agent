#!/usr/bin/env python3
"""Generate eval responses by sending benchmark prompts through Claude API.

Prerequisites:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

Usage:
    python3 scripts/generate_responses.py \
        --benchmark evals/coding-benchmark.jsonl \
        --output runs/20260505/responses.jsonl \
        --model claude-sonnet-4-20250514

    # Dry-run (print prompts without calling API):
    python3 scripts/generate_responses.py \
        --benchmark evals/coding-benchmark.jsonl \
        --output /dev/null \
        --dry-run

    # Resume from where you left off (skip already-generated IDs):
    python3 scripts/generate_responses.py \
        --benchmark evals/coding-benchmark.jsonl \
        --output runs/20260505/responses.jsonl \
        --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_agent_system_prompt() -> str:
    """Load the agent definition as system prompt."""
    agent_path = ROOT / "agents" / "coding-assistant.agent.md"
    text = agent_path.read_text(encoding="utf-8")
    # Strip frontmatter
    if text.startswith("---"):
        end = text.index("---", 3)
        text = text[end + 3:].strip()
    return text


def load_benchmark(path: Path) -> list[dict]:
    """Load benchmark JSONL file."""
    tasks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def load_existing_ids(output_path: Path) -> set[str]:
    """Load IDs already in the output file (for resume mode)."""
    if not output_path.exists():
        return set()
    ids = set()
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                ids.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                pass
    return ids


def extract_packs_from_response(response: str) -> list[str]:
    """Best-effort extraction of pack names mentioned in response."""
    pack_pattern = r"(backend|frontend|mobile|database|api-design|observability|testing|debugging|devops|quality)-pack"
    return list(set(re.findall(pack_pattern, response)))


def call_claude(prompt: str, system: str, model: str) -> dict:
    """Call Claude API and return response + metadata."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: 'anthropic' package not installed. Run: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic()

    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed_ms = int((time.time() - start) * 1000)

    text = response.content[0].text if response.content else ""

    return {
        "response": text,
        "tokens": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
        },
        "latency_ms": elapsed_ms,
        "model": model,
        "stop_reason": response.stop_reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate eval responses via Claude API")
    parser.add_argument("--benchmark", required=True, help="Path to benchmark JSONL")
    parser.add_argument("--output", required=True, help="Path to output responses JSONL")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling API")
    parser.add_argument("--resume", action="store_true", help="Skip tasks already in output file")
    parser.add_argument("--limit", type=int, default=0, help="Max tasks to process (0 = all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls (rate limit)")
    args = parser.parse_args()

    # Validate API key
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Get your key at: https://console.anthropic.com/settings/keys")
        return 1

    benchmark_path = Path(args.benchmark)
    output_path = Path(args.output)

    if not benchmark_path.exists():
        print(f"ERROR: benchmark not found: {benchmark_path}")
        return 1

    # Load
    tasks = load_benchmark(benchmark_path)
    system_prompt = load_agent_system_prompt()
    existing_ids = load_existing_ids(output_path) if args.resume else set()

    # Filter
    tasks_to_run = [t for t in tasks if t["id"] not in existing_ids]
    if args.limit > 0:
        tasks_to_run = tasks_to_run[:args.limit]

    print(f"Benchmark: {benchmark_path.name} ({len(tasks)} total, {len(tasks_to_run)} to run)")
    print(f"Model: {args.model}")
    print(f"Output: {output_path}")
    if existing_ids:
        print(f"Resuming: skipping {len(existing_ids)} already-generated tasks")
    print()

    if args.dry_run:
        for task in tasks_to_run:
            print(f"[{task['id']}] {task['prompt'][:100]}...")
        print(f"\nDry-run complete. {len(tasks_to_run)} tasks would be sent.")
        return 0

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate
    total_tokens = 0
    total_cost_usd = 0.0

    with open(output_path, "a", encoding="utf-8") as f:
        for i, task in enumerate(tasks_to_run, 1):
            print(f"[{i}/{len(tasks_to_run)}] {task['id']}...", end=" ", flush=True)

            try:
                result = call_claude(task["prompt"], system_prompt, args.model)
            except Exception as e:
                print(f"ERROR: {e}")
                # Write error entry
                error_entry = {"id": task["id"], "error": str(e), "response": ""}
                f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
                continue

            # Build output entry
            entry = {
                "id": task["id"],
                "response": result["response"],
                "packs_invoked": extract_packs_from_response(result["response"]),
                "references_invoked": [],  # Would need deeper parsing
                "tokens": result["tokens"],
                "latency_ms": result["latency_ms"],
                "model": result["model"],
            }

            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()

            tokens = result["tokens"]["total"]
            total_tokens += tokens

            # Estimate cost (Claude Sonnet: $3/M input, $15/M output)
            cost = (result["tokens"]["input"] * 3 + result["tokens"]["output"] * 15) / 1_000_000
            total_cost_usd += cost

            print(f"done ({tokens} tokens, {result['latency_ms']}ms, ${cost:.4f})")

            # Rate limit delay
            if i < len(tasks_to_run):
                time.sleep(args.delay)

    print(f"\n{'='*60}")
    print(f"Complete: {len(tasks_to_run)} tasks")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Estimated cost: ${total_cost_usd:.4f}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
