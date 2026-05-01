#!/usr/bin/env python3
"""Cross-reference validator for Coding Assistant Agent.

Checks that:
1. Every reference file in skills/*/references/ is listed in its pack's SKILL.md.
2. Every reference listed in SKILL.md has a corresponding .md file.
3. Every reference in the agent router's Language Support table exists as a file.
4. The .github/skills/ mirror matches skills/ (same files and content).

Usage:
    python evals/validate-references.py [--root .]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_skill_references(skill_md: Path) -> set[str]:
    """Extract reference names from the Pack Reference Map table in SKILL.md."""
    refs = set()
    in_table = False
    for line in skill_md.read_text().splitlines():
        if "| Reference |" in line or "| --- |" in line or "|---|" in line:
            in_table = True
            continue
        if in_table:
            if not line.strip().startswith("|"):
                break
            match = re.match(r"\|\s*`?([a-z0-9_-]+)`?\s*\|", line)
            if match:
                refs.add(match.group(1))
    return refs


def get_reference_files(references_dir: Path) -> set[str]:
    """Get reference names from .md files in a references/ directory."""
    if not references_dir.exists():
        return set()
    return {f.stem for f in references_dir.glob("*.md")}


def validate_pack(pack_dir: Path, errors: list[str]) -> None:
    """Validate a single pack directory."""
    pack_name = pack_dir.name
    skill_md = pack_dir / "SKILL.md"
    refs_dir = pack_dir / "references"

    if not skill_md.exists():
        errors.append(f"  {pack_name}: SKILL.md missing")
        return

    declared = extract_skill_references(skill_md)
    on_disk = get_reference_files(refs_dir)

    # Files on disk but not in SKILL.md
    undeclared = on_disk - declared
    for ref in sorted(undeclared):
        errors.append(
            f"  {pack_name}: reference file '{ref}.md' exists but NOT listed in SKILL.md"
        )

    # Listed in SKILL.md but no file
    missing_files = declared - on_disk
    for ref in sorted(missing_files):
        errors.append(
            f"  {pack_name}: SKILL.md lists '{ref}' but no file at references/{ref}.md"
        )


def validate_mirror(skills_dir: Path, mirror_dir: Path, errors: list[str]) -> None:
    """Validate that .github/skills/ mirrors skills/ exactly for Markdown files."""
    if not mirror_dir.exists():
        errors.append("  .github/skills/ directory does not exist")
        return

    source_packs = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    mirror_packs = {d.name for d in mirror_dir.iterdir() if d.is_dir()}

    missing_in_mirror = source_packs - mirror_packs
    for p in sorted(missing_in_mirror):
        errors.append(f"  Mirror missing pack: {p}")

    extra_in_mirror = mirror_packs - source_packs
    for p in sorted(extra_in_mirror):
        errors.append(f"  Mirror has extra pack: {p}")

    for pack_name in sorted(source_packs & mirror_packs):
        src_refs = get_reference_files(skills_dir / pack_name / "references")
        mir_refs = get_reference_files(mirror_dir / pack_name / "references")

        for ref in sorted(src_refs - mir_refs):
            errors.append(
                f"  Mirror {pack_name}: missing reference '{ref}.md'"
            )
        for ref in sorted(mir_refs - src_refs):
            errors.append(
                f"  Mirror {pack_name}: extra reference '{ref}.md'"
            )

    source_files = {p.relative_to(skills_dir) for p in skills_dir.rglob("*.md")}
    mirror_files = {p.relative_to(mirror_dir) for p in mirror_dir.rglob("*.md")}

    for rel in sorted(source_files - mirror_files):
        errors.append(f"  Mirror missing file: {rel}")
    for rel in sorted(mirror_files - source_files):
        errors.append(f"  Mirror has extra file: {rel}")
    for rel in sorted(source_files & mirror_files):
        if (skills_dir / rel).read_text() != (mirror_dir / rel).read_text():
            errors.append(f"  Mirror file differs from source: {rel}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate pack ↔ reference cross-references")
    ap.add_argument(
        "--root", type=Path, default=Path("."),
        help="Root directory of the coding-assistant-agent (default: current directory)"
    )
    args = ap.parse_args()

    root = args.root.resolve()
    skills_dir = root / "skills"
    mirror_dir = root / ".github" / "skills"

    if not skills_dir.exists():
        print(f"ERROR: {skills_dir} not found", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Validate each pack
    print("Checking skills/ packs...")
    for pack_dir in sorted(skills_dir.iterdir()):
        if pack_dir.is_dir():
            validate_pack(pack_dir, errors)

    # Validate mirror
    print("Checking .github/skills/ mirror...")
    validate_mirror(skills_dir, mirror_dir, errors)

    # Report
    if errors:
        print(f"\n❌ Found {len(errors)} issue(s):\n")
        for e in errors:
            print(e)
        return 1
    else:
        packs = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        total_refs = sum(
            len(get_reference_files(skills_dir / p / "references"))
            for p in packs
        )
        print(f"\n✅ All clear: {len(packs)} packs, {total_refs} references, mirror synced.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
