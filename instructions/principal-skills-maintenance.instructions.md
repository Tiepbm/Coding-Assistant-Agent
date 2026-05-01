---
description: 'Maintenance rules for editing skills/<pack>/SKILL.md and skills/<pack>/references/*.md in the coding-assistant-agent repo. Maintainer-only; NOT loaded at runtime.'
applyTo: 'skills/**/*.md'
---
# Coding Assistant — Skills Maintenance Instructions

## Purpose

Use these instructions when editing or adding `skills/<pack>/SKILL.md` and `skills/<pack>/references/*.md` files. Each top-level pack is a **routing layer + reference map**; deep implementation patterns live in references.

## Package Boundary

- Keep these skills in this standalone repo. Do not commit generated skills back into `awesome-copilot` or into `software-engineering-agent`.
- Preserve the path convention: `skills/<pack>/SKILL.md` plus `skills/<pack>/references/<ref>.md`. Mirror to `.github/skills/<pack>/`.
- The 10 packs are: `backend-pack`, `frontend-pack`, `mobile-pack`, `database-pack`, `api-design-pack`, `observability-pack`, `testing-pack`, `debugging-pack`, `devops-pack`, `quality-pack`.

## Required Skill Frontmatter

Every `SKILL.md` and reference must start with markdown frontmatter:

- `name`: lowercase, hyphen-separated; for SKILL.md it must exactly match the pack folder; for references it must match the filename without extension.
- `description`: concise single-quoted sentence beginning with `'Use when …'`. Length ≥ 30 chars, ≤ 600 chars.

## Pack `SKILL.md` Structure (≤ 100 lines, validator-enforced)

A pack `SKILL.md` MUST contain — in this order — and nothing else:

1. Frontmatter.
2. `# <Pack Title>` (optionally followed by a one-line scope note in `>` blockquote).
3. `## When to Use` (3–8 concrete trigger bullets).
4. `## When NOT to Use` (2–6 anti-triggers pointing to neighbour packs OR to CE7 escalation references).
5. `## Pack Reference Map` (table; one row per reference; **distinct** `Use when` per row).
6. `## Cross-Pack Handoffs` (`→ <other-pack>` and/or `→ software-engineering-agent/skills/<pack>/references/<ref>` bullets).

DO NOT add `Purpose`, `Routing Rules`, `Reference Selection Matrix`, `Expected Output Style`, `Token Efficiency Rules`, or `Quality Gates` sections — those live in `instructions/pack-conventions.instructions.md`.

## Reference (`references/*.md`) Structure (≤ 250 lines, warn at 220)

Every implementation reference must contain:

- Frontmatter.
- `# <Title>` (and optional one-line scope blockquote).
- A **BAD pattern → GOOD pattern** pair with one-line reasoning, OR (for shim refs) a "two scopes — pick the right one" table.
- Imports, types, error handling — never partial snippets.
- A runnable test alongside the implementation (skip only for pure-config or shim refs).
- A `## Cross-Pack Handoffs` section at the end.

### Shim Reference (`*-handoff.md`) Special Rules (≤ 60 lines)

Shim references route a topic to CE7 instead of duplicating the design. They MUST contain:

- Two-scope table: which scope is owned by Coding Assistant vs CE7.
- An always-on Coding Assistant rule list (3–6 bullets).
- A "When to escalate to CE7" table with at least 3 signal/owner-reference rows.
- `Cross-Pack Handoffs` section ending with at least one CE7 reference link.

## Pack Quality Bar

Each pack must be written like a senior+ routing layer:

- Use concrete, enforceable rules; explain trade-offs and rejected shortcuts.
- Include failure modes that actually happen in production.
- Include test expectations next to implementation patterns.
- Avoid vague phrases ("follow best practices") unless followed by specific verification rules.
- Keep guidance applicable to enterprise systems (banking, insurance, transaction-heavy, regulated).
- Detailed instruction lives in `references/`; the pack is for routing.

## Cross-Pack Hygiene

- A reference must not duplicate > 5 lines of content from another reference; replace with `→`.
- A reference must not silently override a rule from `instructions/coding-standards.instructions.md`; if it disagrees, the instruction wins or the instruction must be updated.
- A reference whose decision is owned by CE7 (architecture / governance / SLO / vendor / tenant strategy) MUST be a shim ref (`*-handoff.md`), not a deep playbook.

## Anti-Patterns to Avoid

- Repeating the same boilerplate framework setup across references.
- Adding tool/framework names without "when to use / when to avoid" trade-off.
- Recommending caching/messaging/security patterns that belong in CE7 — escalate via shim ref instead.
- Replacing a decision matrix with prose during "cleanup".
- Letting a reference grow > 250 lines — split or move detail to a focused sub-reference.
- Leaving a reference without a runnable test (except shim refs).

## Review Checklist

Before finalizing a skill change, verify:

- Frontmatter `name` matches folder/filename; `description` starts with `Use when`.
- All sections exist in the required order; pack ≤ 100 lines; reference ≤ 250 lines; shim ≤ 60 lines.
- BAD/GOOD pair present (or "two scopes" table for shim).
- A test accompanies the implementation pattern (or shim is correctly typed).
- `Cross-Pack Handoffs` section exists and includes at least one cross-pack or CE7 link.
- Root `skills/` and `.github/skills/` are synchronized.
- `python3 scripts/validate_packs.py` passes.
- `python3 evals/validate-references.py` passes.
- If the change adds a new reference, the pack's `Pack Reference Map` is updated and the validator's EXPECTED entry is updated.

