---
description: 'Shared conventions for all Coding Assistant pack SKILL.md files. Maintainer-only; NOT loaded at runtime.'
applyTo: 'skills/**/SKILL.md'
---
# Pack Conventions

## Pack Structure (REQUIRED, validator-enforced)

Every pack SKILL.md must have these sections in order:
1. Frontmatter (name matches folder, description starting with "Use when ...", >= 30 chars, <= 600 chars)
2. `# <Pack Title>` (optional one-line scope blockquote)
3. `## When to Use` (3-8 concrete triggers)
4. `## When NOT to Use` (2-6 anti-triggers pointing to neighbor packs OR CE7 escalation refs)
5. `## Pack Reference Map` (table: Reference | Use when - distinct triggers per row)
6. `## Cross-Pack Handoffs` (3-8 bullets: "-> pack/ref" for concern; include at least one CE7 link if pack has shim refs)

## Line Caps (CI-enforced)

| File type | Soft cap (warn) | Hard cap (fail) |
|---|---|---|
| Pack `SKILL.md` | 90 | 100 |
| Implementation reference (`*.md` under `references/`) | 220 | 250 |
| Shim reference (`*-handoff.md`) | 50 | 60 |
| Agent (`agents/*.agent.md`) | 320 | 360 |

If you exceed the soft cap, split content into a new reference rather than letting the file grow.

## Code Output Style

- BAD/GOOD pattern pairs with 1-line reasoning. BAD comes first.
- Include imports, types, error handling - never partial snippets.
- Inline comments only for non-obvious decisions ("why", not "what"); use the inline-ADR shape when justifying a non-trivial choice.
- Always include a test alongside implementation code (skip only for shim refs and pure-config refs).
- Use the project existing style when visible.

## Token Efficiency

- Pack = routing layer; references = code patterns + examples.
- Do not paste large code blocks in pack SKILL.md - keep in references.
- Each reference should cover ONE pattern / ONE technology depth, not three.
- If > 3 references seem necessary for a single response, name the primary one and justify extras.

## Cross-Pack Reference Hygiene

- Distinct triggers per row in `Pack Reference Map`. Two rows that say "Use when writing API code" is a smell - merge or differentiate.
- A pack must not duplicate > 5 lines of another pack content. Replace with "->".
- Cross-pack handoffs must point to packs/refs that actually exist (validator checks).
- Shim references (`*-handoff.md`) MUST link to a CE7 reference path that exists in `../software-engineering-agent/skills/`.

## Quality Gates

- Code compiles/runs without modification.
- Tests are executable (not pseudocode).
- Security patterns applied by default (parameterized queries, tenant authz, no secrets, framework primitives).
- Error handling included (not just happy path).
- For shim refs: two-scope table present, always-on rules present, escalation table present.
