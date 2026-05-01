#!/usr/bin/env python3
"""Validate the Coding Assistant Copilot-first pack layout.

Mirrors the structural checks of software-engineering-agent/scripts/validate_hybrid_packs.py
but for this repo's 10 implementation packs.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "backend-pack": [
        "java-spring-boot",
        "kotlin-spring",
        "dotnet-aspnet-core",
        "nodejs-express",
        "python-fastapi",
        "go-standard",
        "rust-axum",
        "concurrency-patterns",
        "resilience-handoff",
    ],
    "frontend-pack": [
        "react-nextjs",
        "angular",
        "vue-nuxt",
        "accessibility",
        "state-management-advanced",
    ],
    "mobile-pack": [
        "react-native",
        "flutter",
        "swift-ios",
        "kotlin-android",
    ],
    "database-pack": [
        "sql-patterns",
        "orm-patterns",
        "nosql-patterns",
        "migration-safety",
        "storage-search-handoff",
    ],
    "api-design-pack": [
        "openapi-first",
        "graphql-schema",
        "grpc-proto",
        "contract-testing",
    ],
    "observability-pack": [
        "structured-logging",
        "otel-tracing",
        "metrics-instrumentation",
        "runbook-snippets",
    ],
    "testing-pack": [
        "unit-testing",
        "integration-testing",
        "e2e-testing",
        "tdd-workflow",
    ],
    "debugging-pack": [
        "systematic-debugging",
        "performance-debugging",
        "production-debugging",
    ],
    "devops-pack": [
        "docker-containerization",
        "ci-cd-pipelines",
        "infrastructure-as-code",
        "aws-services",
    ],
    "quality-pack": [
        "code-review-patterns",
        "refactoring-patterns",
        "security-coding",
        "feature-flags",
        "release-safety",
        "architecture-handoff",
        "security-handoff",
    ],
}

PACK_HARD_CAP = 100
REF_HARD_CAP = 250
SHIM_HARD_CAP = 60
AGENT_HARD_CAP = 360
EXPECTED_AGENTS = ["coding-assistant.agent.md"]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def check_markdown_links(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if not target or "://" in target or target.startswith("#") or target.startswith("mailto:"):
            continue
        target_path = (path.parent / target.split("#", 1)[0]).resolve()
        if not target_path.exists():
            fail(errors, f"dead markdown link in {path.relative_to(ROOT)} -> {target}")


def check_skill_tree(base: Path, label: str, errors: list[str]) -> None:
    peer_skills = sorted(p.parent.name for p in base.glob("*/SKILL.md"))
    expected_packs = sorted(EXPECTED)
    if peer_skills != expected_packs:
        fail(errors, f"{label}: expected packs {expected_packs}, found {peer_skills}")

    for pack, refs in EXPECTED.items():
        skill = base / pack / "SKILL.md"
        if not skill.exists():
            fail(errors, f"{label}: missing {skill.relative_to(ROOT)}")
            continue
        text = skill.read_text(encoding="utf-8")
        if f"name: {pack}" not in text:
            fail(errors, f"{label}: {skill.relative_to(ROOT)} frontmatter name mismatch")
        if "description: 'Use when" not in text:
            fail(errors, f"{label}: {skill.relative_to(ROOT)} description must use trigger-first 'Use when' phrasing")
        if count_lines(skill) > PACK_HARD_CAP:
            fail(errors, f"{label}: {skill.relative_to(ROOT)} exceeds {PACK_HARD_CAP}-line pack budget")
        for required_section in ("## When to Use", "## When NOT to Use", "## Pack Reference Map", "## Cross-Pack Handoffs"):
            if required_section not in text:
                fail(errors, f"{label}: {skill.relative_to(ROOT)} missing section {required_section!r}")
        check_markdown_links(skill, errors)

        for ref in refs:
            ref_path = base / pack / "references" / f"{ref}.md"
            if not ref_path.exists():
                fail(errors, f"{label}: missing reference {ref_path.relative_to(ROOT)}")
                continue
            ref_text = ref_path.read_text(encoding="utf-8")
            is_shim = ref.endswith("-handoff")
            cap = SHIM_HARD_CAP if is_shim else REF_HARD_CAP
            line_count = count_lines(ref_path)
            if line_count > cap:
                if is_shim:
                    # Strict for new shim refs
                    fail(errors, f"{label}: {ref_path.relative_to(ROOT)} (shim) exceeds {cap}-line cap (got {line_count})")
                else:
                    # Warn-only for legacy implementation refs (allow strict mode via env)
                    msg = f"{label}: {ref_path.relative_to(ROOT)} exceeds {cap}-line soft cap (got {line_count})"
                    if os.environ.get("STRICT_LINE_CAPS") == "1":
                        fail(errors, msg)
                    else:
                        print(f"WARN: {msg}")
            if "description:" not in ref_text:
                fail(errors, f"{label}: {ref_path.relative_to(ROOT)} missing description in frontmatter")
            elif is_shim and "description: 'Use when" not in ref_text:
                fail(errors, f"{label}: {ref_path.relative_to(ROOT)} (shim) description must start with 'Use when'")


def check_agent(errors: list[str]) -> None:
    for sub in ("agents", ".github/agents"):
        agents_dir = ROOT / sub
        if not agents_dir.exists():
            fail(errors, f"missing directory {sub}")
            continue
        names = sorted(p.name for p in agents_dir.glob("*.agent.md"))
        if names != EXPECTED_AGENTS:
            fail(errors, f"{sub}: expected {EXPECTED_AGENTS}, found {names}")
        for name in names:
            path = agents_dir / name
            lines = count_lines(path)
            if lines > AGENT_HARD_CAP:
                fail(errors, f"{sub}/{name} exceeds {AGENT_HARD_CAP}-line agent budget (got {lines})")
            text = path.read_text(encoding="utf-8")
            for required in (
                "Clarify-First Protocol",
                "Self-Review Checklist",
                "Production Readiness Mini-Bar",
                "Auto-Attach Rules",
                "HANDOFF-PROTOCOL.md",
            ):
                if required not in text:
                    fail(errors, f"{sub}/{name} missing required section/keyword: {required!r}")


def check_handoff_protocol(errors: list[str]) -> None:
    path = ROOT / "HANDOFF-PROTOCOL.md"
    if not path.exists():
        fail(errors, "missing HANDOFF-PROTOCOL.md at repo root")
        return
    text = path.read_text(encoding="utf-8")
    for required in (
        "Implementation Input Package",
        "Implementation Return Package",
        "Re-engagement triggers",
        "1.0.0",
    ):
        if required not in text:
            fail(errors, f"HANDOFF-PROTOCOL.md missing required section: {required!r}")


def check_benchmark(errors: list[str]) -> None:
    path = ROOT / "evals" / "coding-benchmark.jsonl"
    if not path.exists():
        fail(errors, "missing evals/coding-benchmark.jsonl")
        return
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(errors, f"coding-benchmark.jsonl:{line_no}: invalid JSON: {exc}")
            continue
        rows.append(row)
        for pack_field in ("expected_pack",):
            pack = row.get(pack_field)
            if pack and pack not in EXPECTED:
                fail(errors, f"coding-benchmark.jsonl:{line_no}: unknown {pack_field} {pack}")
    if len(rows) < 25:
        fail(errors, f"Expected at least 25 coding benchmark rows, found {len(rows)}")


def check_optional_benchmarks(errors: list[str]) -> None:
    """Check handoff and anti-pattern benchmarks if present."""
    for name in ("handoff-benchmark.jsonl", "anti-pattern-benchmark.jsonl"):
        path = ROOT / "evals" / name
        if not path.exists():
            continue  # optional
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                fail(errors, f"{name}:{line_no}: invalid JSON: {exc}")


def check_mirror(errors: list[str]) -> None:
    if os.environ.get("CHECK_GITHUB_MIRROR") != "1":
        return
    if not (ROOT / ".github" / "skills").exists():
        return
    check_skill_tree(ROOT / ".github" / "skills", ".github/skills", errors)


def main() -> int:
    errors: list[str] = []
    check_skill_tree(ROOT / "skills", "skills", errors)
    check_agent(errors)
    check_handoff_protocol(errors)
    check_benchmark(errors)
    check_optional_benchmarks(errors)
    check_mirror(errors)

    total_refs = sum(len(v) for v in EXPECTED.values())

    if errors:
        print("FAIL: coding-assistant pack validation found issues:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: coding-assistant pack layout is valid")
    print(f"- packs: {len(EXPECTED)}")
    print(f"- references: {total_refs}")
    print("- agent: coding-assistant.agent.md (with Clarify-First, Self-Review, Mini-Bar, Auto-Attach, HANDOFF link)")
    print("- HANDOFF-PROTOCOL.md present")
    return 0


if __name__ == "__main__":
    sys.exit(main())

